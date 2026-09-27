# Validation of 0.1.0a1

Local environment: Python 3.12.14, NumPy 2.5.3, rasterio 1.5.1, h5py 3.16.0,
matplotlib 3.11.1; Windows.

The library suite passed **34 tests** after retiring the interface. They exercise GSLC/GCOV/RSLC reading and exports, missing covariance terms,
quad reciprocity/scaling, radar-coordinate guards, HTTP byte-range limits,
measured dual/quad sample statistics, map reprojection, discovery validation,
and figure generation. Synthetic fixtures test numerical and
product-format edge cases; README examples use measured observations.
AOI checks cover GeoJSON, projected GeoPackages, multiple layers, polygon holes,
invalid geometries and missing CRS, candidate limits and missing footprints.
Batch checks compare every quad-pol layer against single-window processing for
GSLC/GCOV/RSLC, including chunk seams, transforms and CRS. They also check AOI
holes, box clipping, bounded reads, trailing look cells, source retention after
simulated processing failure, opt-in deletion after success, cleanup errors,
and parallel batch isolation. Mission-scale throughput and live authenticated
download/cleanup have not been benchmarked.

Both measured samples reproduce every saved metric mean within relative
tolerance 1e-5 and absolute tolerance 1e-8, retaining source windows and looks.
This checks extraction consistency, not independent geophysical accuracy.
The six README panels can be regenerated with `examples/reproduce_figures.py`.
Both distributions build successfully. The wheel was installed into a separate
target directory and generated all 18 quad products using its bundled data.
Distribution metadata passed `packaging.metadata.Metadata` validation.

The local machine had a globally configured legacy Conda PROJ database. Testing
used the PROJ database bundled with the active rasterio installation; the local
PowerShell launcher does the same without changing permanent system settings.

GitHub Actions passed on Python 3.11, 3.12 and 3.13 for the initial private
repository upload (commit b3bed9610555b762cd960ea53186e907967bb5e9;
[workflow run](https://github.com/Cesarito2021/pyNISAR/actions/runs/36297507441)).

Not yet verified: installation/running
on CryoCloud, optional polsartools decompositions in this extraction,
and live authenticated NASA retrieval through pyNISAR. The latest owner instruction
keeps the repository private. Public hosting and PyPI/Zenodo
publication are not authorized.

The dual and quad tutorial notebooks each executed all seven code cells locally
using the bundled measured subsets. Their final three-panel outputs were saved
in the notebooks and copied to the README gallery. Notebook schemas and README
Python syntax were checked. Live NASA retrieval is a separate, unverified path.

The same dual/quad measured workflow cells also completed in Google Colab using
an installed wheel, with three generated figures for each case and the final
`PYNISAR_COLAB_VERIFIED` marker. The separate owner-accessible
[verification notebook](https://colab.research.google.com/drive/1pknUEEGOGjsfA7YC47NWOTDqQSGxFXAN)
contains the run; no sharing settings were changed. This checks the measured-demo
path, not NASA authentication/downloads or the source-ZIP installation chooser.
