"""Small, explicit steps for the NISAR discovery-to-products tutorials."""
import math
from pathlib import Path


def square_aoi(longitude, latitude, *, size_km=5):
    """Create a square in the local UTM CRS and return its WGS84 polygon."""
    import geopandas as gpd
    from shapely.geometry import Point, box
    if not (-180 <= longitude < 180 and -80 <= latitude <= 84):
        raise ValueError('Choose a longitude/latitude within the UTM domain.')
    if not math.isfinite(size_km) or not 0 < size_km <= 20:
        raise ValueError('Use a tutorial square between 0 and 20 km wide.')
    epsg = (32600 if latitude >= 0 else 32700) + int((longitude+180)//6)+1
    point = gpd.GeoSeries([Point(longitude, latitude)], crs=4326).to_crs(epsg).iloc[0]
    half = size_km*500
    return gpd.GeoDataFrame({'name': [f'{size_km:g} km study square']},
        geometry=[box(point.x-half, point.y-half, point.x+half, point.y+half)], crs=epsg).to_crs(4326)


def find_scenes(*, product, aoi, start, end, polarization=None, count=50,
                collection=None, client=None):
    """Find provisional L-band scenes; optional quad filter uses catalogue names.

    A name filter is only screening. Processing checks actual HDF5 channels.
    Pass a collection concept ID to select another release explicitly.
    """
    from .discovery import collections, search, SearchResults
    if product not in ('GSLC', 'GCOV', 'RSLC'):
        raise ValueError('product must be GSLC, GCOV or RSLC.')
    if polarization not in (None, 'quad'):
        raise ValueError('Use polarization=None or quad; select channels when processing.')
    if collection is None:
        matches = [c for c in collections(client=client)
                   if c['short_name'] == f'NISAR_L{1 if product == "RSLC" else 2}_{product}_PROVISIONAL_V1']
        if len(matches) != 1:
            raise ValueError('Provisional V1 collection not uniquely available. Select a concept ID from discovery.collections().')
        collection = matches[0]['concept_id']
    found = search(collection, aoi=aoi, start=start, end=end, count=count, client=client)
    selected = [s for s in found if polarization is None or '_QP' in s['umm']['GranuleUR']]
    selected.sort(key=lambda s: s['umm']['GranuleUR'])
    result = SearchResults(selected, candidate_count=found.candidate_count, limit=count,
                           omitted_footprints=found.omitted_footprints)
    if not result:
        raise ValueError('No matching scenes. Change the area or dates; no scene was selected.')
    return result


def scene_table(scenes):
    """Display catalogue metadata with row numbers matching scenes[index]."""
    import pandas as pd
    records = []
    for scene in scenes:
        u = scene['umm']
        records.append({'scene': u['GranuleUR'],
            'acquired_utc': u.get('TemporalExtent', {}).get('RangeDateTime', {}).get('BeginningDateTime'),
            'collection': u.get('CollectionReference', {}).get('ShortName')})
    return pd.DataFrame(records, columns=['scene', 'acquired_utc', 'collection'])


def plot_search(scenes, aoi):
    """Plot catalogue footprints and the study area; labels match table indices."""
    import geopandas as gpd
    from .discovery import footprint as scene_footprint
    from matplotlib import pyplot as plt
    from .aoi import read_aoi
    area = read_aoi(aoi)
    fig, ax = plt.subplots(figsize=(7, 5), layout='constrained')
    for i, scene in enumerate(scenes):
        footprint = scene_footprint(scene)
        gpd.GeoSeries([footprint], crs=4326).boundary.plot(ax=ax, color='#287c9d', linewidth=.8)
        center = footprint.representative_point()
        ax.text(center.x, center.y, str(i), fontsize=8)
    area.plot(ax=ax, color='#ef8a24', edgecolor='black', alpha=.8)
    ax.set(xlabel='Longitude', ylabel='Latitude', title='NISAR scene footprints and study area (orange)')
    ax.ticklabel_format(useOffset=False)
    return fig


def process_scene(scene, output, *, aoi, channels, reciprocal=False,
                  frequency='A', looks=(1, 1), max_mb=512, session=None):
    """Read only a small map AOI by HTTPS ranges; never download a whole scene.

    Reads at most 4096 native pixels per side. Polygon masking uses output pixel
    centers. HDF5 channels/covariance are validated by the native reader.
    """
    from .remote import open_remote
    urls = [u for u in scene.data_links() if u.split('?')[0].lower().endswith('.h5')]
    if len(urls) != 1:
        raise ValueError('Expected one HDF5 data link in this scene.')
    with open_remote(urls[0], max_mb=max_mb, session=session) as source:
        return process_area(source, output, aoi=aoi, channels=channels,
                            reciprocal=reciprocal, frequency=frequency, looks=looks)


def process_area(source, output, *, aoi, channels, reciprocal=False,
                 frequency='A', looks=(1, 1)):
    """Process a small polygon from a local or seekable remote map product."""
    import h5py
    import numpy as np
    import rasterio
    from affine import Affine
    from rasterio.features import geometry_mask
    from .aoi import read_aoi
    from .products import _group, _channels, _selection, read_window
    from .analysis import _export_window
    from .polarimetry import _validate
    _validate(('HH',), 256, looks)
    area = read_aoi(aoi)
    with h5py.File(source, 'r') as h:
        product, group = _group(h, frequency)
        if product == 'RSLC':
            raise ValueError('Geographic AOIs require GSLC or GCOV; RSLC is in radar geometry.')
        available = _channels(group, product)
        shape = group[available[0]*2 if product == 'GCOV' else available[0]].shape
        _, _, crs = _selection(group, product, None, None, max(looks), looks, shape)
        dx, dy = float(group['xCoordinateSpacing'][()]), float(group['yCoordinateSpacing'][()])
        transform = Affine(dx, 0, float(group['xCoordinates'][0])-dx/2,
                           0, dy, float(group['yCoordinates'][0])-dy/2)
        projected = area.to_crs(crs)
        from shapely.ops import transform as transform_geometry
        pixel_bounds = transform_geometry(lambda x,y,z=None: (~transform)*(x,y),
                                            projected.geometry.union_all()).bounds
        ly,lx = looks
        c0 = max(0, math.floor(pixel_bounds[0]/lx)*lx)
        r0 = max(0, math.floor(pixel_bounds[1]/ly)*ly)
        c1 = min(shape[1]//lx*lx, math.ceil(pixel_bounds[2]/lx)*lx)
        r1 = min(shape[0]//ly*ly, math.ceil(pixel_bounds[3]/ly)*ly)
        if c1 <= c0 or r1 <= r0:
            raise ValueError('Study area does not overlap this scene.')
        if max(r1-r0,c1-c0) > 4096:
            raise ValueError('AOI too large for a tutorial read; use process_tile for chunked local processing.')
    window = read_window(source, frequency=frequency, channels=channels, looks=looks,
                         raster_window=(r0,c0,r1-r0,c1-c0))
    mask = geometry_mask(projected.geometry, out_shape=next(iter(window.intensity.values())).shape,
                         transform=window.transform, invert=True)
    for values in window.intensity.values():
        values[~mask] = np.nan
    if window.covariance is not None:
        window.covariance[~mask] = np.nan
    if not any(np.isfinite(v).any() for v in window.intensity.values()):
        raise ValueError('No finite radar samples in this area; choose another scene or area.')
    window.info.update(aoi_geojson=area.geometry.union_all().__geo_interface__,
                       aoi_mask='output pixel centers', scope='aoi')
    return _export_window(window, output, reciprocal=reciprocal)
