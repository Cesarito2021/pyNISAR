# Release candidate status

pyNISAR 0.1.0a1 is a research alpha candidate. GitHub remains private; no PyPI
or Zenodo release has been published. The license is GPL-3.0-only, identical to
PyGeoObserver. The related RSASE manuscript is under review, not published.

See [VALIDATION.md](VALIDATION.md) for installed-wheel tests and live dual/quad
CryoCloud executions. Automated CI checks fresh wheel installation and tests on
Python 3.11–3.14. It never publishes the package.

Before authorizing a public alpha release:

1. Confirm the latest CI jobs pass and review the included notebooks and figures.
2. Confirm the PyPI distribution name and owner account/trusted publisher.
3. Decide when to make GitHub public and update access instructions accordingly.
4. Build the approved commit, check both distributions and publish only with
   explicit owner approval. Keep the alpha version until broader validation.

Local development checks:

```bash
python -m pip install ".[dev]"
python -m pytest -q
python -m build
python -m twine check dist/*
```
