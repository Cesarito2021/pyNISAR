# Development status

**Keep the app local and the GitHub repository private.** This is the owner's
latest instruction and supersedes the earlier public-app deployment plan.
Do not deploy to Streamlit Cloud, create a public tunnel, change GitHub visibility,
upload to PyPI or create a Zenodo release without a new explicit instruction.

- Repository: https://github.com/Cesarito2021/pyNISAR (private).
- Local launcher: `Start-pyNISAR.ps1`, using http://127.0.0.1:8517.
- No hosted app exists. No hosting sign-in is required for local use.
- The local address works only on the computer running the app.
- License: GPL-3.0-only, identical to PyGeoObserver.
- Manuscript: submitted to RSASE; not yet published.

## Local checks

```bash
python -m pip install ".[app,dev]"
pytest -q
python -m build
```

Building a wheel or source archive does not publish it. The GitHub workflow runs
checks and builds only; it has no deployment or package-publishing step.
