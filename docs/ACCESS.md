# Areas, NASA access and storage

## Define a study area

`search()` accepts one of:

- `bbox=(west, south, east, north)` in longitude/latitude, WGS84.
- `aoi="study_area.geojson"` with Polygon or MultiPolygon boundaries.
- `aoi="study_area.gpkg", layer="boundary"` with a declared CRS.
- `aoi=geodataframe` with polygon geometry and a declared CRS.

GeoPackage coordinates are transformed to WGS84 automatically. Choose a layer
explicitly if a GeoPackage contains more than one. Empty/invalid geometries,
point layers and ambiguous CRS are rejected. Split an AOI crossing the antimeridian
before searching. The local app accepts files or manually entered box coordinates;
it does not yet support drawing a rectangle on the map.

For polygons, the library queries NASA CMR using the enclosing box, then keeps
only candidate footprints that intersect the actual polygon union, including
holes. Missing/invalid footprints are omitted with a warning. `count` limits
candidates before filtering, so a limit warning means the result may be incomplete.
Narrow the dates or area, or raise `count` up to 100. A search selects whole NISAR
scenes/granules; it does not crop the downloaded HDF5 file to the AOI.

```python
from pynisar.discovery import collections, search

available = collections()
print(available)  # Choose the product/version and copy its concept_id.
# collection_id = "chosen concept_id"
# scenes = search(collection_id, aoi="study_area.gpkg", layer="boundary",
#                 start="2025-11-01", end="2025-11-10", count=50)
```

## Credentials

Public catalogue search and the bundled examples need no NASA account.
Protected NISAR downloads and authenticated remote reads need the user's own
[NASA Earthdata Login](https://urs.earthdata.nasa.gov/).

Authenticate in the Python/notebook session:

```python
import earthaccess
auth = earthaccess.login(persist=False)
# Choose the granules to download after inspecting the search results.
# files = earthaccess.download([scenes[0]], local_path="data/nisar")
```

`persist=False` avoids saving credentials through this call. Earthaccess can also
use existing environment credentials or a previously configured `.netrc`.
Never put passwords in the README, notebooks, GitHub files or exported scripts.
The local app searches and prepares example Python code; it does not log in to
NASA or download complete mission files itself.

See [Earthaccess authentication](https://earthaccess.readthedocs.io/en/latest/user/explanation/authenticate/)
and [data access](https://earthaccess.readthedocs.io/en/stable/user/explanation/access/).

## Storage and processing

No separate cloud bucket or paid storage account is required. Users provide an
output folder on their computer, mounted drive or notebook filesystem. Full NISAR
HDF5 scenes can be several GB; allow room for selected inputs and derived products.
Source data remain at NASA/ASF until requested. The GitHub checkout includes only
the software and two small measured demonstration subsets.

The library's `open_remote(url, max_mb=128)` can read supported HTTPS byte ranges
without saving a complete scene. `max_mb` caps response-body bytes per file
instance, not total RAM or output storage; a subset can still exceed that budget.
Authentication and byte-range support are required. Derived products still need
an output folder. Remote reading does not supply a storage service.

Native processing reads bounded windows, not full-scene mosaics or AOI-shaped
pixel clips. GSLC/GCOV can use `center=(longitude, latitude)`; RSLC uses
`pixel=(row, column)` and remains in radar coordinates.

The app runs locally and uses temporary session folders. Save its ZIP download
to keep results. The Python API writes to the output folder you choose. Notebook
storage lifetime depends on the notebook service; save retained files to your
own persistent storage before ending the session.
