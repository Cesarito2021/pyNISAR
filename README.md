<p align="center"><img src="docs/banner.svg" alt="pyNISAR — NISAR L-band SAR in Python" width="100%"></p>

**Discover, process and visualize NISAR L-band SAR.**

Developed by **Cesar Alvites**. pyNISAR extracts the NISAR workflow from
[PyGeoObserver](https://github.com/Cesarito2021/pygeoobserver): find scenes,
inspect GSLC/GCOV/RSLC files, calculate polarimetric products and export figures.

**Research alpha · private GitHub repository · local app · GPL-3.0-only.**

## Get started

Python 3.11 or newer. From this project folder:

```bash
python -m pip install ".[plot,discovery]"
```

Try the measured example without a NASA account:

```python
import pynisar

run = pynisar.process_sample("outputs", mode="dual")
pynisar.plot(run)
pynisar.plot_halpha(run)
```

The same Python API is intended for local Jupyter, Colab and CryoCloud.
[Notebook example](examples/notebook_quickstart.ipynb) · [Processing example](examples/process_nisar.py).

## Search, credentials and storage

| Question | Answer |
|---|---|
| How do I define the study area? | A GeoJSON polygon, GeoPackage polygon layer, or WGS84 bounding box: west, south, east, north. |
| Do I need NASA credentials? | **No** for public catalogue search or bundled examples. **Yes** for protected downloads and remote reads: use your own [Earthdata Login](https://urs.earthdata.nasa.gov/). |
| Do I need a cloud-storage account? | **No.** Choose a folder on your computer or notebook filesystem. |
| How much storage? | Full HDF5 scenes can be several GB. Allow space for selected inputs and outputs. Remote window reads can avoid saving the entire scene. |
| Does the AOI crop the download? | **No.** It selects intersecting scenes; a full download still retrieves the whole HDF5 file. |

Choose a NISAR collection with `collections()`, then search by area and date:

```python
from pynisar.discovery import collections, search

print(collections())  # Choose the product/version and its collection_id.
# Set collection_id to the selected concept_id before searching.
scenes = search(collection_id, aoi="study_area.geojson",
                start="2025-11-01", end="2025-11-10")
# Alternatives: aoi="study_area.gpkg", layer="boundary"
#              bbox=(-90.3, 46.35, -90.1, 46.55)
```

GeoPackages are reprojected from their declared CRS. Polygon searches filter
candidate footprints to the actual boundary. If the candidate limit is reached,
narrow the area/dates or increase `count`; results may otherwise be incomplete.

For downloads, log in from your own Python session with
`earthaccess.login(persist=False)`, then download selected scenes to a chosen folder.
[Access, storage and download example](docs/ACCESS.md).

## Products

- **GeoTIFFs:** measured powers and supported intensity/polarimetric descriptors.
- **Figures:** power maps, H–α density and quad-pol H–A–α diagrams; PNG and SVG.
- **Records:** statistics CSV, covariance and a processing manifest with provenance.

Choose **AOI-only** or **entire-tile** products. Large files are read in chunks;
tiles can run sequentially or with optional parallel workers:

```python
results = pynisar.process_batch(
    ["scene_1.h5", "scene_2.h5"], "products",
    scope="aoi", aoi="study_area.gpkg", layer="boundary",
    chunk_size=256, workers=1, reciprocal=True,
    delete_source=False,  # True: delete each HDF5 only after successful export.
)
print(results)  # Check each tile's status.
# For the whole tile: scope="tile". For a box: bbox=(west, south, east, north).
```

Each tile gets separate compressed GeoTIFFs and a processing record. Start with
one worker for quad-pol; parallel workers multiply memory use. To save disk,
download and process one scene at a time, optionally deleting its HDF5 afterward.
[Batch processing, cleanup and limits](docs/BATCH.md).

Phase descriptors require complex covariance;
quad-pol processing requires measured HH/HV/VH/VV and explicit reciprocity.
RSLC stays in radar coordinates and supports entire-tile processing, not geographic
AOI clipping. Terrain correction and carbon prediction are not included.
[Definitions and limits](docs/POLARIMETRY.md).

## Measured examples

**Dual polarization · GSLC.** HH/HV selected from a measured quad acquisition;
uncorrected mean |S|² shown in dB, with H–α in the dual C2 basis.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/dual_hh.png" alt="HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/dual_hv.png" alt="HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–α · 2D</strong><br><img src="docs/figures/panels/dual_halpha.png" alt="Dual H–alpha" width="100%"></td>
</tr></table>

**Full polarization · GCOV.** All four measured channels; power as stored
(nominal γ⁰), with H–A–α from reciprocal Pauli T3.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/quad_hh.png" alt="HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/quad_hv.png" alt="HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–A–α · 3D</strong><br><img src="docs/figures/panels/quad_haalpha.png" alt="Quad H–A–alpha" width="100%"></td>
</tr></table>

Western Great Lakes · 6 November 2025. These are separate from the manuscript's
Amazon–Cerrado study area. The banner uses measured **VH** from the quad example.
[Sources](docs/figures/panels/sources.json) · [Reproduce figures](examples/reproduce_figures.py).

## Optional local app

```bash
python -m pip install ".[app]"
streamlit run streamlit_app.py --server.address 127.0.0.1
```

The browser is the interface; Python runs on your computer. Search with an AOI
file or box coordinates, explore examples, or process a small HDF5 upload.
NASA login and full-file downloads use the Python workflow above. Save the ZIP
export to retain temporary app outputs. The app is **local only**; no hosting
account is needed. [Development status](docs/RELEASE.md).

## Citation

Alvites et al. *Early assessment of NISAR L-band SAR and multi-sensor fusion for
aboveground carbon mapping in the Brazilian Amazon–Cerrado ecotone.*
**Submitted to Remote Sensing Applications: Society and Environment; not yet published.**
[Full author list and software citation](CITATION.cff). No publication DOI is assigned.

## Acknowledgments and license

Cesar Alvites thanks **CryoCloud** for access to its Python/Jupyter environment,
supported by NASA grants **80NSSC22K1877** and **80NSSC23K0002**. Manuscript
processing was performed in **Google Colab**. [CryoCloud guidance](https://book.cryointhecloud.com/citing-cryocloud).

**GPL-3.0-only**, matching PyGeoObserver. [License](LICENSE) · [Source and logo credits](docs/PROVENANCE.md).
Independent research software; no NASA/ISRO endorsement.
