"""NISAR GSLC, GCOV and RSLC access and polarimetry."""
from pynisar.products import inspect_product as inspect, read_window as read
from pynisar.analysis import analyze_product as polarimetry
from pynisar.product_plots import plot_product as plot
from pynisar.decompositions import decompose
from pynisar.remote import open_remote

__all__ = ['inspect','read','polarimetry','plot','decompose','open_remote',
           'plot_halpha','plot_haalpha','plot_htheta']


def _metrics(run, names):
    import json
    from pathlib import Path
    import numpy as np
    import rasterio
    run = Path(run)
    report = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    if report['status'] != 'complete':
        raise ValueError('Select a completed analysis run.')
    arrays, grids = [], []
    for name in names:
        if name not in report['metrics']:
            raise ValueError(f'This run does not contain {name}.')
        path = run/report['metrics'][name]['file']
        if not path.resolve().is_relative_to(run.resolve()):
            raise ValueError('Metric path must stay inside its analysis run.')
        with rasterio.open(path) as ds:
            arrays.append(ds.read(1,masked=True).astype(float).filled(np.nan))
            grids.append((ds.crs, ds.transform, ds.shape))
    if any(grid != grids[0] for grid in grids[1:]):
        raise ValueError('Metric grids differ.')
    return run, report, arrays


def plot_halpha(run, output=None, *, zones=False, **options):
    """Plot H–alpha directly from a completed dual/co/quad analysis directory."""
    from pynisar.halpha import plot_halpha as draw
    run, report, arrays = _metrics(run, ['entropy','alpha'])
    mode = 'quad' if len(report['channels']) == 4 else 'dual'
    return draw(*arrays, output or run/'halpha', mode=mode, zones=zones, **options)


def plot_haalpha(run, output=None, **options):
    """Plot the three H/A/alpha marginal densities from a completed quad run."""
    from pynisar.halpha import plot_haalpha as draw
    run, report, arrays = _metrics(run, ['entropy','anisotropy','alpha'])
    if len(report['channels']) != 4:
        raise ValueError('H–A–alpha requires a quad-pol analysis.')
    return draw(*arrays, output or run/'haalpha', **options)


def plot_htheta(run, output=None, **options):
    """Plot compatible MF3CF H/theta arrays from a decomposition directory."""
    from pathlib import Path
    import json
    import numpy as np
    import rasterio
    from pynisar.halpha import plot_htheta as draw
    from pynisar.grid import check_raster_alignment
    run=Path(run)
    report=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    if report['status'] != 'complete':
        raise ValueError('Select a completed MF3CF decomposition.')
    paths=[run/'input/H_fp.tif',run/'input/Theta_FP_mf3cf.tif']
    check_raster_alignment(paths)
    arrays=[]
    for path in paths:
        with rasterio.open(path) as ds:
            arrays.append(ds.read(1,masked=True).astype(float).filled(np.nan))
    return draw(*arrays, output or run/'htheta', **options)
