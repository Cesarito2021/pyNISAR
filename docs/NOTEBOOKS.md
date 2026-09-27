# Run the dual and quad notebooks

1. With access to this private repository, download its source ZIP and either
   `examples/pyNISAR_dual.ipynb` or `examples/pyNISAR_quad.ipynb`.
2. In Colab choose **File → Upload notebook**. Run the installation cell; when
   prompted upload the source ZIP. Direct Colab/GitHub links depend on your
   private-repository authorization. No token is embedded in the notebook.
3. In local Jupyter/CryoCloud, install `.[plot,discovery,notebook]` from the extracted
   project and open the notebook with your existing Jupyter environment.
4. **Run all** with `LIVE=False` to reproduce real bundled observations. NASA
   credentials are unnecessary. This mode ignores the entered AOI and retains
   the sample's recorded spatial support and looks.
5. Set `LIVE=True` to search/read NASA observations. Change the box or use a
   GeoJSON/GeoPackage, dates and scene selection as needed; sign in to Earthdata.
   The default reference is a measured quad acquisition over the western Great
   Lakes on 6 November 2025. The dual case selects its HH/HV channels.
6. `DOWNLOAD_H5=False` reads a bounded remote window with a 256 MiB response-body
   budget. `True` downloads a whole source HDF5. A small AOI does not crop that
   download. Neither mode silently downloads a complete file when range access fails.

The notebooks display the real power and polarimetric figures and save GeoTIFFs,
CSV statistics, covariance and a processing manifest. A scene name/polarization
code does not replace dataset inspection: incomplete covariance cannot support
full polarimetric descriptors. If no suitable scene is found, change the AOI or
date window; do not substitute invented data.

Use `process_tile`/`process_batch` for full AOI or tile outputs, as described in
[BATCH.md](BATCH.md). Plotting examples intentionally use small bounded windows.
No notebook contains a NASA password or a GitHub token. Keep retained products
on persistent storage before closing an ephemeral notebook runtime.
