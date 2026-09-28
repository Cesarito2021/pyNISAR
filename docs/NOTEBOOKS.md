# Run the dual and quad notebooks

1. Download the source ZIP and a `pyNISAR_dual.ipynb` or `pyNISAR_quad.ipynb`
   notebook from this repository.
2. Rename the ZIP `pynisar_source.zip` and upload it beside the notebook in
   Jupyter/CryoCloud. In Colab, upload the notebook through **File → Upload notebook**,
   then upload the ZIP through the Files sidebar.
3. Run `%pip install ./pynisar_source.zip`. Discovery, plotting and notebook
   dependencies are installed automatically. No R is required.
4. Run the remaining cells in order: import, create a 5 km square, sign in with
   your own NASA Earthdata account, search, map, choose one scene, process and plot.
5. Change the coordinates or supply your GeoJSON/GeoPackage to use another AOI.
   Change the row index to select another scene. If no scene matches, adjust the
   area or dates before selecting.

Both notebooks retain real CryoCloud outputs from 28 September 2026. The
installation cell was simplified after execution and its old output cleared;
the processing cells retain their original execution counts and outputs.
Both use one quad GCOV observation: the dual case selects HH/HV, while the quad
case uses HH/HV/VH/VV with an explicit reciprocity assumption.

Only the small AOI is read and masked. Each remote run has a 512 MiB response-body
budget and a 4,096-pixel limit per native raster side. Neither notebook downloads
a complete HDF5. Keep exported GeoTIFFs, statistics and the manifest on persistent
storage before closing an ephemeral session. No credentials are embedded.

For larger AOIs, tiles or multiple downloaded files, see [BATCH.md](BATCH.md).
