"""pyNISAR explorer: run with streamlit run streamlit_app.py."""
from datetime import date
from pathlib import Path
import io
import json
import tempfile
import zipfile

import streamlit as st
import streamlit.components.v1 as components
import pynisar
from pynisar.maps import product_map
from pynisar.product_plots import POWER

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title='pyNISAR · Radar explorer', page_icon='🛰️', layout='wide')
st.markdown('''<style>
.block-container {padding-top:4rem; max-width:1600px}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid="stSidebar"] {border-right:1px solid #d5e1dc}
[data-testid="stMetric"] {background:white; border:1px solid #dce7e2; padding:16px; border-radius:12px}
</style>''', unsafe_allow_html=True)

if 'workspace' not in st.session_state:
    st.session_state.workspace = tempfile.TemporaryDirectory(prefix='pynisar-')
workspace = Path(st.session_state.workspace.name)

with st.sidebar:
    st.title('pyNISAR')
    st.caption('LOCAL L-BAND RADAR EXPLORER')
    page = st.radio('Workspace', ['Explore & generate', 'Find observations', 'Figures', 'About & cite'])
    st.divider()
    st.caption('GSLC · GCOV · RSLC\n\nResearch alpha · 0.1.0a1')


def download_run(run):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(run))
    st.download_button('Download products · ZIP', buffer.getvalue(), file_name=run.name+'.zip', mime='application/zip')


if page == 'Explore & generate':
    st.caption('OBSERVATIONS → POLARIMETRY → PRODUCTS')
    st.title('Read the landscape in L-band.')
    st.write('Explore measured NISAR examples and generate georeferenced layers, statistics and scientific figures.')
    with st.sidebar:
        source = st.selectbox('Input', ['Measured example', 'Upload NISAR HDF5 subset'])
        if source == 'Measured example':
            mode = st.selectbox('Polarization', ['dual', 'quad'], format_func=lambda x: 'HH / HV · GSLC' if x=='dual' else 'HH / HV / VH / VV · GCOV')
            key = 'example_'+mode
            if key not in st.session_state:
                st.session_state[key] = str(pynisar.process_sample(workspace, mode=mode))
            run = Path(st.session_state[key])
        else:
            upload = st.file_uploader('HDF5 subset · up to 64 MB', type=['h5','hdf5'])
            st.caption('For full mission files, use the library in your own Python environment.')
            run = None
            if upload is not None:
                import hashlib
                digest = hashlib.sha256(upload.getbuffer()).hexdigest()
                key = 'upload_'+digest
                input_path = workspace/(digest+'.h5')
                if not input_path.exists():
                    input_path.write_bytes(upload.getbuffer())
                frequency = st.selectbox('Frequency', ['A','B'])
                try:
                    metadata = pynisar.inspect(input_path, frequency=frequency)
                    channels = st.multiselect('Measured channels', metadata['channels'], default=metadata['channels'])
                    size = st.select_slider('Window width (source pixels)', [32,64,128,256,512], value=128)
                    looks_y = st.number_input('Row looks', min_value=1, max_value=16, value=2)
                    looks_x = st.number_input('Column looks', min_value=1, max_value=16, value=2)
                    reciprocal = st.checkbox('Assume HV/VH reciprocity for quad-pol', value=False)
                    st.caption('Processes a window at the file center. Use the library to choose a geographic center or radar pixel.')
                    configuration = (frequency, tuple(channels), size, looks_y, looks_x, reciprocal)
                    if st.button('Process selected window', type='primary'):
                        with st.spinner('Deriving NISAR products…'):
                            st.session_state[key] = (configuration, str(pynisar.process(input_path, workspace, frequency=frequency,
                                channels=channels, window_size=size, looks=(int(looks_y),int(looks_x)), reciprocal=reciprocal)))
                    if key in st.session_state and st.session_state[key][0] == configuration:
                        run = Path(st.session_state[key][1])
                except (ValueError, OSError, KeyError) as exc:
                    st.error(str(exc))
    if run is None:
        st.info('Choose a measured example or upload a supported NISAR HDF5 subset to begin.')
    else:
        report = json.loads((run/'manifest.json').read_text())
        with st.sidebar:
            metric = st.selectbox('Map layer', list(report['metrics']), index=list(report['metrics']).index('HH') if 'HH' in report['metrics'] else 0)
            palette = st.selectbox('Color palette', ['gray','viridis','YlGnBu','magma'])
        a,b,c = st.columns(3)
        a.metric('Product', report['product']); b.metric('Polarization', ' / '.join(report['channels']))
        c.metric('Available layers', len(report['metrics']))
        if report['geometry'] == 'map':
            map_, scale = product_map(run/report['metrics'][metric]['file'], metric=metric, cmap=palette)
            components.html(map_.get_root().render(), height=560)
            unit = 'dB display' if metric in POWER else ('degrees' if metric=='alpha' else 'metric values')
            st.caption(f'{metric} · {scale[0]:.3g} to {scale[1]:.3g} {unit} · 2–98% display stretch · {report["radiometry"]}')
        else:
            import rasterio
            import matplotlib.pyplot as plt
            from pynisar.display import _db, _limits
            with rasterio.open(run/report['metrics'][metric]['file']) as ds:
                values = ds.read(1)
            shown = _db(values) if metric in POWER else values
            fig, ax = plt.subplots(); lo,hi = _limits(shown)
            im=ax.imshow(shown, cmap=palette, vmin=lo, vmax=hi)
            ax.set(xlabel='Output column', ylabel='Output row', title='RSLC · radar coordinates')
            fig.colorbar(im, ax=ax); st.pyplot(fig); plt.close(fig)
        if source == 'Measured example':
            st.caption('Western Great Lakes · 6 November 2025 · measured example from PyGeoObserver. This is separate from the Amazon–Cerrado manuscript study area.')
        if report['skipped']:
            st.info('Unavailable descriptors: '+'; '.join(report['skipped']))
        left,right = st.columns([1,2])
        with left:
            if st.button('Generate scientific figures', type='primary'):
                with st.spinner('Rendering figures from the calculated products…'):
                    fig = pynisar.plot(run, dpi=130)
                    pynisar.report(run)
                    if 'entropy' in report['metrics']:
                        pynisar.plot_halpha(run, dpi=130)
                    if len(report['channels']) == 4:
                        pynisar.plot_haalpha(run, dpi=130)
                st.success('Figures and report added to the download.')
            download_run(run)
        with right:
            with st.expander('Processing and provenance'):
                st.json(report)
        if (run/'case_study.png').exists():
            st.image(str(run/'case_study.png'))

elif page == 'Find observations':
    st.title('Find NISAR observations')
    st.write('Choose a box or polygon file, then search NISAR scenes by date. Search needs no NASA login. Downloads need your Earthdata account and space on your computer.')
    from pynisar.discovery import collections, search
    from pynisar.aoi import read_aoi
    area_frame, area_path, area_layer = None, None, None
    area_valid = True
    with st.sidebar:
        if st.button('Load NASA collections'):
            try:
                st.session_state.collections = collections()
            except Exception:
                st.error('NASA collection discovery is unavailable. Please try again later.')
        items = st.session_state.get('collections', [])
        selected = st.selectbox('Collection', items, format_func=lambda x:x['short_name']+' · '+x['version']) if items else None
        area_input = st.radio('Study area', ['Bounding box', 'GeoJSON / GeoPackage'])
        west, south, east, north = -90.3, 46.35, -90.1, 46.55
        if area_input == 'Bounding box':
            west = st.number_input('West longitude', -180.,180.,-90.3)
            east = st.number_input('East longitude', -180.,180.,-90.1)
            south = st.number_input('South latitude', -90.,90.,46.35)
            north = st.number_input('North latitude', -90.,90.,46.55)
            area_valid = west < east and south < north
            if not area_valid:
                st.error('West must be smaller than east; south must be smaller than north.')
        else:
            area_upload = st.file_uploader('Polygon boundary', type=['geojson','json','gpkg'])
            area_valid = False
            if area_upload is not None:
                import hashlib
                area_path = workspace/(hashlib.sha256(area_upload.getbuffer()).hexdigest()+Path(area_upload.name).suffix.lower())
                if not area_path.exists():
                    area_path.write_bytes(area_upload.getbuffer())
                try:
                    if area_path.suffix == '.gpkg':
                        import geopandas as gpd
                        layers = gpd.list_layers(area_path)['name'].tolist()
                        area_layer = st.selectbox('GeoPackage layer', layers)
                    area_frame = read_aoi(area_path, layer=area_layer)
                    west, south, east, north = area_frame.total_bounds.tolist()
                    area_valid = True
                    st.caption('Polygons transformed to WGS84. Search results are filtered to their actual boundaries.')
                except Exception as exc:
                    st.error('Cannot read this AOI: '+str(exc))
        start = st.date_input('From', date(2025,11,1)); end = st.date_input('To', date(2025,11,10))
        candidate_limit = st.selectbox('Maximum candidate scenes', [20,50,100])
        requested = dict(start=str(start), end=str(end), count=candidate_limit, concept_id=selected['concept_id'] if selected else None)
        if area_input == 'Bounding box':
            requested['bbox'] = [west,south,east,north]
        else:
            requested.update(aoi=str(area_path) if area_path else None, layer=area_layer)
        if st.button('Search observations', disabled=not (selected and area_valid)):
            try:
                st.session_state.search_result = (requested, search(**requested))
            except Exception as exc:
                st.error('Search failed: '+str(exc))
    import folium
    map_ = folium.Map(location=[(south+north)/2,(west+east)/2], zoom_start=7, tiles='OpenStreetMap')
    if area_valid:
        if area_frame is not None:
            folium.GeoJson(json.loads(area_frame.to_json()), name='Study area',
                style_function=lambda _:dict(color='#12796f',weight=3,fillOpacity=0.06)).add_to(map_)
        else:
            folium.Rectangle([[south,west],[north,east]], color='#12796f', fill=False).add_to(map_)
        map_.fit_bounds([[south,west],[north,east]])
    saved = st.session_state.get('search_result')
    rows = []
    if saved and saved[0] == requested:
        for granule in saved[1]:
            try:
                folium.GeoJson(granule.__geo_interface__).add_to(map_)
            except (AttributeError, ValueError, TypeError):
                pass
            rows.append({'Name':granule['umm'].get('GranuleUR',''), 'ID':granule['meta']['concept-id']})
        st.caption(f'{len(rows)} matching scenes from {saved[1].candidate_count} candidates.')
        if saved[1].limit_reached:
            st.warning('Candidate limit reached. Narrow the area/dates or increase the limit; coverage may be incomplete.')
        if saved[1].omitted_footprints:
            st.warning(f'{saved[1].omitted_footprints} candidates had no usable footprint and were omitted.')
    components.html(map_.get_root().render(), height=560)
    if rows:
        st.dataframe(rows, use_container_width=True)
    st.caption('The AOI selects intersecting scenes; it does not clip the downloaded HDF5 files. Keep enough disk space for the selected files and outputs. No separate cloud-storage account is needed.')
    if selected and area_valid:
        with st.expander('Large-file Python workflow'):
            st.caption('These settings generate Python code to run locally or in your notebook. The app does not start a full-tile job.')
            output_scope = st.radio('Products cover', ['AOI only', 'Entire tile'])
            block_size = st.selectbox('Input chunk size (pixels per side)', [128,256,512,1024], index=1)
            tile_workers = st.number_input('Concurrent tile workers', min_value=1, max_value=4, value=1)
            cleanup_h5 = st.checkbox('Delete each local HDF5 after successful product export', value=False)
            assume_reciprocal = st.checkbox('Use the reciprocity assumption for quad-pol descriptors', value=False)
            st.caption('Start with one worker for quad-pol. Smaller chunks reduce memory, not the size of complete source downloads. Failed jobs retain their HDF5 files.')
        spatial_code = f'bbox={(west,south,east,north)!r}' if area_input == 'Bounding box' else f'aoi={area_upload.name!r}' + (f', layer={area_layer!r}' if area_layer else '')
        st.code(f'''from pynisar.discovery import search
from pynisar import process_batch
import earthaccess
granules = search({selected['concept_id']!r}, {spatial_code},
                  start={str(start)!r}, end={str(end)!r}, count={candidate_limit})
earthaccess.login(persist=False)
# Inspect granules first, then explicitly select those to process:
selected_granules = []  # e.g. [granules[0]]
for granule in selected_granules:
    files = earthaccess.download([granule], local_path="data")
    results = process_batch(
        files, "products", scope={('aoi' if output_scope == 'AOI only' else 'tile')!r},
        {spatial_code}, chunk_size={block_size}, workers={int(tile_workers)},
        reciprocal={assume_reciprocal}, delete_source={cleanup_h5})
    print(results)
    if any(r['status'] != 'complete' or r.get('cleanup_error') for r in results):
        raise RuntimeError("Inspect the failed job or cleanup error before continuing.")''', language='python')

elif page == 'Figures':
    st.title('Measured examples. Reproducible figures.')
    st.write('The original PyGeoObserver NISAR gallery, preserving its figure style and data provenance.')
    for mode, labels, names in [('dual',['HH','HV','H–α · 2D'],['dual_hh','dual_hv','dual_halpha']),
                                 ('quad',['HH','HV','H–A–α · 3D'],['quad_hh','quad_hv','quad_haalpha'])]:
        st.subheader('Dual polarization · GSLC' if mode=='dual' else 'Full polarization · GCOV')
        for column,label,name in zip(st.columns(3),labels,names):
            column.image(str(ROOT/'docs/figures/panels'/f'{name}.png'), caption=label)
    st.caption('Western Great Lakes · 6 November 2025. GSLC: uncorrected mean |S|²; GCOV: as stored, nominal γ⁰. Quad descriptors explicitly assume reciprocity.')

else:
    st.title('Built for reproducible NISAR research.')
    st.write('pyNISAR is a NISAR-only extraction of PyGeoObserver. The same Python API can be used locally or in Jupyter, Google Colab and CryoCloud.')
    st.subheader('Related manuscript · submitted')
    st.write('Early assessment of NISAR L-band SAR and multi-sensor fusion for aboveground carbon mapping in the Brazilian Amazon–Cerrado ecotone.')
    st.write('Cesar Alvites, Carlos Alberto Silva, Inacio Thomaz Bueno, Ana Paula Dalla Corte, Caio Hamamura, José Augusto Spiazzi Favarin, Lucas Bielak Rezende, Gabriel Máximo Da Silva, Fabiano Rodrigues Pereira, Alexander J. Gaskins, Ruben Valbuena, Viswanath Nandigam, Chelsea Scott, Na Chen, Carine Klauberg, and Andrew Hudak.')
    st.caption('Submitted to Remote Sensing Applications: Society and Environment; not yet published. No publication year or DOI is assigned here.')
    st.subheader('Acknowledgments')
    st.write('The author thanks CryoCloud for providing access to its Python/Jupyter environment, supported by NASA grants 80NSSC22K1877 and 80NSSC23K0002. The manuscript processing was performed in Google Colab.')
    st.link_button('CryoCloud acknowledgment guidance','https://book.cryointhecloud.com/citing-cryocloud')
    st.caption('Research software · GPL-3.0-only, matching PyGeoObserver. No NASA/ISRO endorsement. Source product calibration and quality flags require product-specific assessment.')
