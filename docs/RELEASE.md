# Public app, private GitHub repository

The owner's current instruction is to make the **web app public** while keeping
**Cesarito2021/pyNISAR private on GitHub**. This supersedes the earlier restriction
on public app hosting. It does not authorize publishing the repository, uploading
the package to PyPI or creating a Zenodo deposit.

## Current state

The code is in the private repository:
https://github.com/Cesarito2021/pyNISAR

The local preview runs at http://127.0.0.1:8517 on the computer running the
launcher. That address cannot open the app from a phone or another computer.
Public Streamlit deployment is prepared but waiting for the owner to sign in.
No public app URL exists yet.

## Deploy the public app

Streamlit supports public apps backed by private GitHub repositories. Follow
[the deployment guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
and [the app visibility guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app).

1. Sign in at https://share.streamlit.io/ and handle the account's terms of service.
2. Connect the required GitHub access for this private repository. Review any
   new access request with the owner; never change the repository to public.
3. Create an app with repository `Cesarito2021/pyNISAR`, branch `main`, entrypoint
   `streamlit_app.py`, and Python 3.12. Dependencies are in `requirements.txt`.
4. An app from a private repository starts private. After deployment, use the
   app's Sharing settings to select **This app is public and searchable**.
   This app visibility change is explicitly authorized by the owner.
5. Verify the app works without signing in and separately verify GitHub still
   reports the repository as private. Only then record the actual app URL in README.

Use the free hosting tier. Do not activate a paid service or change repository
visibility to work around access problems. No credentials are needed by visitors
for the bundled examples. Protected NASA downloads run in visitors' own Python
sessions; the app does not collect Earthdata credentials.

The demo uses small measured subsets. HDF5 uploads are limited to 64 MB and
processing to windows of at most 512 source pixels per side. Outputs are
session-specific and temporary. Download results to retain them. The app is not
a full-scene processing cluster; use local Python or Jupyter for larger products.

## License and citation

Retain **GPL-3.0-only**, identical to PyGeoObserver. The LICENSE files were checked
byte-for-byte. Preserve attribution in NOTICE and docs/PROVENANCE.md.

Software credit is Cesar Alvites. The manuscript's 16 authors follow the supplied
submission cover sheet. Keep it marked **submitted; not yet published** until
its status changes. No publication year or DOI is assigned here.

## Local checks

```bash
python -m pip install ".[app,dev]"
pytest -q
python -m build
streamlit run streamlit_app.py --server.address 127.0.0.1
```

The PowerShell launcher starts the local preview on port 8517. Building wheels
and source archives does not publish them.
