# AOI or entire tile, with controlled storage

Install `.[discovery]` for polygon files and NASA access. Use `process_tile()` for
one saved HDF5, or `process_batch()` for several. The app's search page generates
this Python workflow; large jobs run in your local Python or notebook session.

## Choose the output extent

- `scope="aoi"`: supply `aoi="area.geojson"`, a GeoPackage plus `layer=`, a
  GeoDataFrame, or `bbox=(west, south, east, north)` in WGS84. GSLC/GCOV outputs
  cover the intersecting rectangle, with pixels outside the polygons set to NoData.
- `scope="tile"`: process the native tile. An AOI used to find the scene does not
  clip its output. RSLC supports this mode in radar pixel coordinates, without a
  map CRS or terrain correction.

```python
from pynisar import process_tile, process_batch

run = process_tile(
    "scene.h5", "products", scope="aoi", aoi="area.gpkg", layer="boundary",
    chunk_size=256, looks=(2, 2), reciprocal=True, delete_source=False,
)
# Process existing local files concurrently, if RAM and disk throughput permit:
results = process_batch(
    ["scene_1.h5", "scene_2.h5"], "products", scope="tile",
    chunk_size=256, workers=2, reciprocal=True,
)
print(results)  # A failed tile is reported; other tiles can finish.
```

`reciprocal=True` explicitly permits reciprocal C3/T3 descriptors for quad-pol.
It does not create missing covariance terms. Use `channels=["HH","HV"]` to
process those measured channels, or `metrics=["HH","HV"]` to save fewer available
products. Selecting metrics reduces output storage; the current calculation still
derives the supported descriptor set within each chunk.

## Keep the source inventory small

After inspecting and selecting the search results, download one granule, process
it, and optionally delete its local HDF5 before downloading the next:

```python
import earthaccess
from pynisar import process_batch

earthaccess.login(persist=False)
selected_granules = []  # Set this to the search results you choose to process.
for granule in selected_granules:
    files = earthaccess.download([granule], local_path="data/nisar")
    results = process_batch(
        files, "products", scope="aoi", aoi="area.geojson",
        chunk_size=256, workers=1, reciprocal=True, delete_source=True,
    )
    print(results)
    if any(r["status"] != "complete" or r.get("cleanup_error") for r in results):
        raise RuntimeError("Inspect the failed job or cleanup error before continuing.")
```

The default is `delete_source=False`. Setting it to `True` permanently deletes
the explicitly supplied local HDF5 after the GeoTIFF writers close, grids are
verified, statistics are saved, and the manifest records completion. Failed
processing, empty outputs or a source changed during processing prevent deletion.
Cleanup errors are recorded separately; completed products remain available.
No directory is recursively cleaned, and nothing is deleted from NASA storage.

## Memory, products and scientific limits

- `chunk_size=256` means at most 256 × 256 **input pixels** per read. Default
  `workers=1`; up to four tile workers are allowed. Begin with one for quad-pol.
  Memory scales with chunk area, channels and workers; this is not a fixed RAM cap.
- Outputs are compressed tiled BigTIFFs, one layer per metric, in a separate run
  folder for each source. Files are written incrementally without collecting the
  whole tile in RAM. Full covariance archives and additional C3 rasters are not
  saved in this workflow. No cross-tile mosaic or automatic large-image figure is
  generated. Use the small-window workflow for the existing figure gallery.
- `looks` uses the same boxcar average as the original reader, aligned to the
  source origin across chunk boundaries. Incomplete trailing look cells are
  omitted and their pixel counts recorded. AOI membership uses output pixel
  centers **after** averaging, so a boundary look cell can include input pixels
  outside the AOI. Holes are preserved; no spatial filtering halo is applied.
- Per-tile statistics use finite output pixels: count, fraction, min, mean, max,
  population standard deviation. An exact median is omitted to avoid gathering
  the entire raster. The manifest records extent, looks, products and cleanup.
- Interrupted/failed jobs retain their source and partial output folder. They
  are not resumable yet; a retry creates a new run. If the process is terminated,
  its manifest may remain `running`. Remove unwanted partial runs explicitly.
- Chunking saves RAM, while sequential download/cleanup saves input disk space.
  One entire HDF5 and its outputs still need to fit locally. Retained derived
  outputs accumulate. No storage account or hosted worker is supplied.

Numerical equivalence and failure handling are tested using small GSLC, GCOV and
RSLC fixtures. Mission-scale throughput and live authenticated download/cleanup
have not yet been benchmarked.
