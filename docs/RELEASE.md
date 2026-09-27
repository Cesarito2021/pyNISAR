# Development status

pyNISAR is a Python library with downloadable Jupyter/Colab notebooks.
The GitHub repository remains private. Repository access is needed to download
its source and notebooks. No PyPI or Zenodo release has been published.
The license is GPL-3.0-only, identical to PyGeoObserver.
The related RSASE manuscript is under review, not published.

```bash
python -m pip install ".[plot,discovery,dev]"
pytest -q
python -m build
```

The workflow checks and builds distributions; it does not publish them.
