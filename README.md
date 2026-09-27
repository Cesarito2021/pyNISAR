<p align="center"><img src="docs/banner.svg" alt="pyNISAR — NISAR L-band SAR in Python" width="100%"></p>

**Discover NISAR scenes, process SAR data and generate polarimetric products.**

Developed by **Cesar Alvites**, using the NISAR workflow from
[PyGeoObserver](https://github.com/Cesarito2021/pygeoobserver).
**Research alpha · private repository · local app · GPL-3.0-only.**

## Setup

Python 3.11 or newer. Install from this project folder:

```bash
python -m pip install ".[plot,discovery]"
```

Run this setup before either workflow. Replace the area, dates and preview center
for your study; the center must lie within the selected scene.

```python
from pathlib import Path
import earthaccess
import pynisar
from pynisar.discovery import collections, search

area = {"bbox": (-90.3, 46.35, -90.1, 46.55)}
# Or: area = {"aoi": "study_area.geojson"}
# Or: area = {"aoi": "study_area.gpkg", "layer": "boundary"}
dates = {"start": "2025-11-01", "end": "2025-11-10"}
center = (-90.2, 46.45)  # Longitude, latitude for a small figure preview.
scope = "aoi"           # "aoi" or "tile": extent of the saved products.
```

| Access and storage | What you need |
|---|---|
| Search / bundled examples | No NASA credentials. |
| Protected downloads | Your own [Earthdata Login](https://urs.earthdata.nasa.gov/). |
| Storage | A local/notebook folder; no cloud-storage account required. HDF5 scenes can be several GB. |
| AOI | Selects scenes for download; `scope="aoi"` clips derived products. Downloads remain whole files. |

Choose a collection/version and scene explicitly in the steps below. A collection
does not guarantee a scene's polarizations; inspect the downloaded file.
[Access details](docs/ACCESS.md).

## Dual polarization · HH/HV

**Step 1 — Discover GSLC scenes.** Select the collection ID and scene index from
the listed metadata. This example uses measured HH/HV channels.

```python
print([c for c in collections() if "GSLC" in c["short_name"]])
scenes = search(input("GSLC concept_id: ").strip(), **area, **dates, count=20)
print([(i, s["umm"]["GranuleUR"]) for i, s in enumerate(scenes)])
scene = scenes[int(input("Scene index: "))]
```

**Step 2 — Download and inspect.** Confirm that frequency A contains HH and HV.

```python
earthaccess.login(persist=False)
files = earthaccess.download([scene], local_path="data/dual")
source = next(Path(p) for p in files if Path(p).suffix.lower() in (".h5", ".hdf5"))
print(pynisar.inspect(source))
```

**Step 3 — Set looks and generate products.** Write AOI-only or entire-tile
GeoTIFFs in chunks. Keep the HDF5 for the figure preview in Step 4.

```python
settings = {"frequency": "A", "channels": ["HH", "HV"], "looks": (4, 2)}
products = pynisar.process_tile(
    source, "outputs/dual", **settings, **area, scope=scope,
    chunk_size=256, delete_source=False,
)
```

**Step 4 — Generate the figures.** Create a bounded preview from the same scene,
then save the product panels and dual-pol H–α density as PNG/SVG.

```python
preview = pynisar.process(source, "figures/dual", **settings,
                         center=center, window_size=256)
pynisar.plot(preview, metrics=["HH", "HV", "entropy", "alpha"])
pynisar.plot_halpha(preview)
```

To try Step 4 **without downloading**, replace its first call with
`preview = pynisar.process_sample("figures/dual", mode="dual")`.

Measured example: HH/HV from a quad GSLC acquisition; uncorrected mean |S|² in dB,
with H–α in the dual C2 basis.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/dual_hh.png" alt="Measured dual HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/dual_hv.png" alt="Measured dual HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–α · 2D</strong><br><img src="docs/figures/panels/dual_halpha.png" alt="Dual H–alpha density" width="100%"></td>
</tr></table>

## Quad polarization · HH/HV/VH/VV

**Step 1 — Discover GCOV scenes.** Select a collection and a scene with all four
channels and complex covariance terms.

```python
print([c for c in collections() if "GCOV" in c["short_name"]])
scenes = search(input("GCOV concept_id: ").strip(), **area, **dates, count=20)
print([(i, s["umm"]["GranuleUR"]) for i, s in enumerate(scenes)])
scene = scenes[int(input("Scene index: "))]
```

**Step 2 — Download and inspect.** Missing complex cross terms cannot support the
full quad-pol descriptor set; processing checks their availability.

```python
earthaccess.login(persist=False)
files = earthaccess.download([scene], local_path="data/quad")
source = next(Path(p) for p in files if Path(p).suffix.lower() in (".h5", ".hdf5"))
print(pynisar.inspect(source))
```

**Step 3 — Set looks and generate products.** Explicitly assume reciprocity to
form C3/Pauli T3 and calculate the supported 18-layer quad-pol profile.

```python
settings = {"frequency": "A", "channels": ["HH", "HV", "VH", "VV"],
            "looks": (1, 1), "reciprocal": True}
products = pynisar.process_tile(
    source, "outputs/quad", **settings, **area, scope=scope,
    chunk_size=256, delete_source=False,
)
```

**Step 4 — Generate the figures.** Save power/descriptor panels and the quad-pol
H–A–α diagram from a bounded preview of the same scene.

```python
preview = pynisar.process(source, "figures/quad", **settings,
                         center=center, window_size=128)
pynisar.plot(preview, metrics=["HH", "HV", "VH", "VV"])
pynisar.plot_haalpha(preview)
```

To try Step 4 **without downloading**, replace its first call with
`preview = pynisar.process_sample("figures/quad", mode="quad")`.

Measured example: GCOV power as stored (nominal γ⁰), with H–A–α from reciprocal
Pauli T3. These examples show the bundled observations, not an arbitrary search result.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/quad_hh.png" alt="Measured quad HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/quad_hv.png" alt="Measured quad HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–A–α · 3D</strong><br><img src="docs/figures/panels/quad_haalpha.png" alt="Quad H–A–alpha diagram" width="100%"></td>
</tr></table>

Both galleries: western Great Lakes · 6 November 2025, separate from the
manuscript's Amazon–Cerrado study area. The banner uses measured quad **VH**.
[Source windows](docs/figures/panels/sources.json) ·
[Reproduce these exact six panels](examples/reproduce_figures.py).

## Batch processing and cleanup

For several local HDF5 files, use the chosen `settings`, `area` and `scope`:

```python
results = pynisar.process_batch(
    ["scene_1.h5", "scene_2.h5"], "outputs/batch", **settings, **area,
    scope=scope, chunk_size=256, workers=1, delete_source=False,
)
print(results)  # Check each tile's status.
```

Start with one worker for quad-pol. Optional parallel workers increase memory
use. `delete_source=True` removes each HDF5 only after successful export; finish
any source-based previews first. Downloading and processing one scene at a time
reduces input disk usage. [Batch and cleanup guide](docs/BATCH.md).

Products include GeoTIFFs, statistics CSV and a processing manifest. Small-window
runs also retain covariance. RSLC remains in radar coordinates and cannot use a
geographic AOI mask. Terrain correction and carbon prediction are not included.
[Scientific definitions](docs/POLARIMETRY.md) · [Validation](docs/VALIDATION.md).

## Optional local app

```bash
python -m pip install ".[app]"
streamlit run streamlit_app.py --server.address 127.0.0.1
```

Search scenes, generate Python workflow code, explore examples or process a small
HDF5 upload. Save the ZIP export to keep temporary app results. Large jobs use the
Python workflow above. The app stays **local**; no hosting account is required.
[Notebook example](examples/notebook_quickstart.ipynb) · [Development status](docs/RELEASE.md).

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
