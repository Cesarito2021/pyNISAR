# Private development — no publication authorized

**Owner instruction: keep pyNISAR private and unpublished.**

Do not publish the code, documentation, datasets, package artifacts or app.
If a GitHub repository is created in future authorized work, it must be private.
Public release or hosting requires a new explicit instruction from Cesar Alvites.
The earlier discussion of public hosting is superseded by this instruction.
The local app launcher binds to 127.0.0.1; do not expose it through a public tunnel.

The license remains **GPL-3.0-only**, identical to PyGeoObserver. The LICENSE
files were verified byte-for-byte. Preserve existing attribution in NOTICE.

## Deferred release reference — do not execute

The steps below are retained only as notes for a possible future change of
direction. They are not the current plan and do not authorize any upload,
repository creation, public release or deployment.

Current status: private research-alpha package and Python app. The private GitHub
repository is [Cesarito2021/pyNISAR](https://github.com/Cesarito2021/pyNISAR).
Sign in to GitHub as its owner or an authorized collaborator to view it.
No public repository, PyPI distribution, release DOI or public app URL has been created.
The local app runs at http://127.0.0.1:8517 on the computer running the launcher;
that address cannot open the app on a phone or another computer.

A private hosted app is pending Streamlit account sign-in and verification that
access is restricted. Do not deploy with public visibility.

## Release metadata

Software credit is Cesar Alvites. The manuscript's 16 authors and their order
have been transcribed from the corresponding author's submission cover sheet.
Keep the paper marked "submitted; not yet published" until its status changes.
Add a public preprint or publication URL and bibliographic dates when available.
Check PyPI name availability immediately before creating the distribution; no
claim or reservation of `pynisar` is implied by the project metadata.
Retain GPL-3.0-only and PyGeoObserver attribution for extracted code.

## GitHub and software archive

Create `Cesarito2021/pyNISAR`, upload this project, and run the included CI.
Tag a tested release, e.g. `v0.1.0a1`. Connect that repository to Zenodo before
publishing the GitHub release if a software DOI is desired. Add the actual
repository URL and assigned DOI to README and CITATION.cff afterward.
The manuscript DOI and software DOI describe different research outputs.

## Python Package Index

```bash
python -m pip install ".[app,dev]"
pytest -q
python -m build
python -m twine check dist/*
```

Configure a PyPI trusted publisher or use your own PyPI credentials to upload the
reviewed distribution. Never commit a token. A successful local build does not
mean a release has been published. See [PyPI publishing](https://packaging.python.org/en/latest/tutorials/packaging-projects/).

## Free Python app hosting

[Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud)
provides free app hosting linked to GitHub. Sign in with the repository owner's
account, select the repository and branch, set `streamlit_app.py` as the entrypoint,
and choose Python 3.12. The root `requirements.txt` installs the package and app
dependencies. Keep `.streamlit/config.toml` in the repository.

The demo calculates products from two small, measured, bundled subsets. HDF5
uploads are limited to 64 MB and processing windows to 512 source pixels per side.
Public NASA catalog search needs connectivity; authenticated downloads are left
to visitors' own Python sessions. Temporary outputs are session-specific and
not durable storage. Download results before leaving the app.

Free hosting has changing CPU/memory limits and apps may sleep when inactive;
it is not a full-scene NISAR processing cluster. Use Colab, CryoCloud or local
Jupyter for larger products. [Resource guidance](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app).

The public deployment requires the repository owner's hosting login. Record and
verify the actual live URL before adding an app badge to the README.
