# Validation of 0.1.0a1

Validation date: **28 September 2026**. This is a research alpha candidate;
Public release was subsequently authorized; PyPI setup is in progress.

## Installed distribution on Windows

A new virtual environment with system-site-packages disabled was created using
Python 3.12.14. The wheel was installed into its own site-packages; tests disabled
the repository's source-path override, so they exercised the installed package.
Dependencies were installed separately because the execution sandbox blocked
network access and the elevated installer could not read the locally built wheel.
`pip check` reported no broken requirements. This verifies an isolated installation;
automatic dependency installation from the wheel is additionally checked by CI.

- **38 tests passed.** Coverage includes GSLC/GCOV/RSLC reading, missing covariance,
  reciprocal quad processing, polygon masks and holes, chunk seams, parallel batch
  isolation, source retention on failure and opt-in source deletion.
- Discovery now supports both Earthaccess GeoJSON footprints and older UMM polygon
  metadata. A regression test verifies preservation of polygon holes.
- Both bundled measured examples produced **18 metric layers and three figures**.
  GeoTIFFs had map CRS and finite samples. Saved reference means matched within
  relative tolerance 1e-5 and absolute tolerance 1e-8.
- CLI help worked. Wheel and source distribution passed `twine check`.
- The local legacy Conda PROJ environment was overridden for these processes only,
  using the active rasterio installation's PROJ database.

Packages: NumPy 2.5.3, h5py 3.16.0, rasterio 1.5.1, GeoPandas 1.1.4,
Earthaccess 0.19.0 and matplotlib 3.11.2.

## Live NASA workflow on CryoCloud

Both notebooks completed all 11 code cells using Python 3.14.7 and Earthaccess
0.18.0 on Linux. Existing NASA credentials authenticated without being copied
into notebooks. The library was installed from the uploaded source ZIP.

- Search returned two quad GCOV scenes, acquired on 6 and 18 November 2025.
- Row 0 selected the 6 November Great Lakes acquisition.
- Each run read a **5 × 5 km AOI** by authenticated HTTPS byte ranges, with a
  512 MiB response-body limit; no complete HDF5 was downloaded.
- Both exports contain **18 metric layers and 62,500 valid AOI pixels** inside a
  251 × 251 raster window, EPSG:32615. The mask excludes border pixel centers.
- Dual uses HH/HV from the quad acquisition; quad uses all four measured channels
  and explicitly assumes reciprocity. GCOV power is used as stored (nominal γ⁰).
- The notebooks retain tables and figures. The README uses the same processing
  steps and the resulting figures, not the earlier bundled-subset gallery.

Evidence: [dual manifest](figures/cryocloud/dual_manifest.json),
[quad manifest](figures/cryocloud/quad_manifest.json),
[dual statistics](figures/cryocloud/dual_statistics.csv),
[quad statistics](figures/cryocloud/quad_statistics.csv), and the two notebooks.
The installation cell was simplified after execution and its output cleared;
all processing-cell outputs are retained. Manuscript processing remains Google
Colab; these CryoCloud executions validate the library tutorials separately.

## Limits before publication

This confirms software execution and sample consistency, not independent
geophysical accuracy. Optional PolSARtools decompositions and mission-scale
throughput are not part of this validation. The two-channel tutorial is a subset
of a quad acquisition, not a separate dual-only acquisition.

The CI workflow builds and installs the wheel on Python 3.11–3.14, runs the
suite against that installation and checks distribution metadata. See the
repository Actions results for the current commit before releasing.
The owner subsequently authorized a public alpha release. Publishing requires
the PyPI account connection described in RELEASE.md. No credentials are stored
in the repository.
