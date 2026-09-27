<p align="center"><img src="docs/banner.svg" alt="pyNISAR" width="100%"></p>

# pyNISAR

**NISAR L-band SAR processing, polarimetric products and reproducible figures in Python.**

Inspect GSLC, GCOV and RSLC products, process a bounded window, explore measured
polarizations and export GeoTIFFs, statistics and scientific figures. Extracted
from [PyGeoObserver](https://github.com/Cesarito2021/pygeoobserver), with a focused
API and a map explorer inspired by [als_downloader](https://github.com/Cesarito2021/als_downloader).

**Version 0.1.0a1 · private research alpha.** Keep this project private and
unpublished. No public repository, PyPI release, Zenodo deposit or public app
deployment is authorized. Any future GitHub repository must be private unless
Cesar Alvites explicitly changes this instruction. pyNISAR is independent
research software and does not claim NASA/ISRO affiliation or endorsement.

**Private repository:** [Cesarito2021/pyNISAR](https://github.com/Cesarito2021/pyNISAR)
(GitHub sign-in required). **App:** currently local at `http://127.0.0.1:8517`
on the computer running the launcher. A private hosted app is not yet deployed.

## Install

Python 3.11 or newer. From this project directory:

```bash
python -m pip install ".[plot,discovery]"
```

For the app:

```bash
python -m pip install ".[app]"
streamlit run streamlit_app.py
```

The app places input, polarization and layer controls on the left, with the map
on the right. It includes measured examples, small HDF5 uploads, NASA collection
search, figure generation, and a ZIP export of products and provenance.
[Private development and release policy](docs/RELEASE.md) · [Python and notebook examples](examples).

## First products · no account needed

```python
import pynisar

# A real, already multilooked GSLC HH/HV subset bundled with the library.
run = pynisar.process_sample("outputs", mode="dual")
pynisar.plot(run)                   # PNG + SVG product panel
pynisar.plot_halpha(run)            # H–α density
pynisar.report(run)                 # Methods, provenance and summary statistics

quad = pynisar.process_sample("outputs", mode="quad")
pynisar.plot_haalpha(quad)           # H–A–α from reciprocal Pauli T3
```

The samples re-derive products from the stored measured covariance. They do not
repeat the looks already applied to the samples. Every output includes a manifest
with source, native window, channels, radiometry and processing assumptions.

## NISAR · Dual polarization

HH and HV power maps, followed by the **2D H–α diagram**.
This GSLC example selects HH/HV from a measured quad acquisition.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/dual_hh.png" alt="HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/dual_hv.png" alt="HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–α · 2D</strong><br><img src="docs/figures/panels/dual_halpha.png" alt="Dual H–alpha" width="100%"></td>
</tr></table>

GSLC power is uncorrected mean |S|², shown in dB; the diagram uses the dual C2 basis.

## NISAR · Full / quad polarization

HH and HV previews alongside the **3D H–A–α diagram**.
Processing uses all four measured channels: HH, HV, VH and VV.

<table><tr>
<td width="33%" align="center"><strong>HH</strong><br><img src="docs/figures/panels/quad_hh.png" alt="HH power" width="100%"></td>
<td width="33%" align="center"><strong>HV</strong><br><img src="docs/figures/panels/quad_hv.png" alt="HV power" width="100%"></td>
<td width="33%" align="center"><strong>H–A–α · 3D</strong><br><img src="docs/figures/panels/quad_haalpha.png" alt="Quad H–A–alpha" width="100%"></td>
</tr></table>

GCOV power is shown as stored (nominal γ⁰). The diagram uses reciprocal Pauli T3;
its cube faces show three 2D density projections. Both examples are measured
western Great Lakes subsets acquired **6 November 2025**, separate from the
Amazon–Cerrado study area in the related manuscript.

[Source details](docs/figures/panels/sources.json) ·
[Code and data provenance](docs/PROVENANCE.md) ·
[Recreate the panels](examples/reproduce_figures.py).

## Process your own observation

```python
import pynisar

info = pynisar.inspect("observation.h5", frequency="A")
print(info["product"], info["channels"])

run = pynisar.process(
    "observation.h5", "outputs",
    frequency="A", channels=["HH", "HV"],
    window_size=256, looks=(4, 2),
)
```

For map products, use `center=(longitude, latitude)` to select a location.
For RSLC, use `pixel=(row, column)`; outputs retain radar coordinates.
For measured HH/HV/VH/VV, pass all four channels and `reciprocal=True` explicitly.
GCOV products without complex cross terms receive intensity products only.

| Input | Supported native outputs | Interpretation |
|---|---|---|
| GSLC / RSLC co-cross dual-pol | Up to 18 intensity and covariance descriptors | Cross terms derived from complex samples; dual H uses log₂ |
| GCOV co-cross dual-pol | Up to 18; 10 intensity descriptors if cross terms are absent | Stored covariance; no invented phase |
| HH / VV co-pol | Power, ratios and covariance descriptors when available | Co-pol Pauli basis |
| Measured HH / HV / VH / VV | 18-layer profile, reciprocal C3, Pauli powers, H/A/α | Explicit reciprocity assumption; full H uses log₃ |
| Single polarization | Measured intensity | No inferred polarimetric descriptors |
| Compact-pol | Inspection and reading | Interpretation is not implemented |

The reader processes bounded windows, not full-scene mosaics. It does not perform
terrain correction, independent radiometric calibration, InSAR, or carbon prediction.
Carbon estimates require a separately validated model and reference observations.
[Metric definitions and scientific limits](docs/POLARIMETRY.md).
Optional model-based decompositions use `.[decompositions]` and a compatible GDAL
environment; those backends were not newly validated in this extraction.

## NASA discovery and remote access

```python
from pynisar.discovery import collections, search
import earthaccess
import pynisar

available = collections()  # Inspect current versions and collection IDs first.
# observations = search(selected_concept_id, bbox=(-90.3, 46.35, -90.1, 46.55),
#                       start="2025-11-01", end="2025-11-10")
earthaccess.login(persist=False)
# with pynisar.open_remote(selected_hdf5_url, max_mb=128) as source:
#     run = pynisar.process(source, "outputs", channels=["HH", "HV"])
```

Authentication is needed for protected NASA files. The remote reader requires
HTTPS byte-range support and enforces a response-body byte budget. The public
demo uses bundled subsets and does not ask visitors for Earthdata credentials.

## Jupyter, Google Colab and CryoCloud

The processing API uses ordinary Python paths and arrays, with no Colab-specific
imports. Install into the notebook kernel using `%pip install ".[plot,discovery]"`
from the project directory. The same API is intended for local Jupyter, Google
Colab and CryoCloud; this extraction has been tested locally, not yet on both
hosted notebook services. Full NISAR products can exceed free app resources;
use your own notebook environment for larger work.

## Citation and related manuscript

Please cite the software version you use. [CITATION.cff](CITATION.cff) records the
software separately from the related manuscript:

Cesar Alvites, Carlos Alberto Silva, Inacio Thomaz Bueno, Ana Paula Dalla Corte,
Caio Hamamura, José Augusto Spiazzi Favarin, Lucas Bielak Rezende,
Gabriel Máximo Da Silva, Fabiano Rodrigues Pereira, Alexander J. Gaskins,
Ruben Valbuena, Viswanath Nandigam, Chelsea Scott, Na Chen, Carine Klauberg,
and Andrew Hudak. *Early assessment of NISAR L-band SAR and multi-sensor fusion for aboveground carbon
mapping in the Brazilian Amazon–Cerrado ecotone.* Submitted to **Remote Sensing
Applications: Society and Environment**; **submitted manuscript, not yet published**.

Author order follows the submission cover sheet supplied by the corresponding
author. No publication year, journal volume, pages, acceptance date or DOI is
assigned to this unpublished manuscript. Update the reference when a public
preprint or published version becomes available. A software DOI
should be added after archiving an actual release.

## Acknowledgments

The author thanks **CryoCloud** for providing access to its Python/Jupyter
environment, supported by NASA grants **80NSSC22K1877** and **80NSSC23K0002**.
The manuscript processing was performed in **Google Colab**.

This wording follows CryoCloud's acknowledgment option and describes the support
received without attributing the manuscript computations to CryoCloud.
[Official acknowledgment guidance](https://book.cryointhecloud.com/citing-cryocloud) ·
[CryoCloud JupyterBook, Snow et al. (2023)](https://doi.org/10.5281/zenodo.7576601).

## Development

```bash
python -m pip install ".[app,dev]"
pytest -q
python -m build
```

GPL-3.0-only. Original NISAR code and figures are attributed to PyGeoObserver.
See [NOTICE](NOTICE), [LICENSE](LICENSE) and [release preparation](docs/RELEASE.md).
