"""Reproducible three-panel gallery from a small completed analysis run."""
from pathlib import Path
import numpy as np
import rasterio


def plot_gallery(run, *, dpi=160):
    """Save HH, HV and H-alpha/H-A-alpha PNGs from a bounded analysis run.

    Uses nearest-neighbor display, a fixed -25..5 dB power stretch, and the
    existing polarimetric density routines. Intended for small example windows.
    """
    import json
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from .nisar import plot_halpha, plot_haalpha
    run = Path(run)
    report = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    if report['status'] != 'complete':
        raise ValueError('Use a complete analysis run.')
    if not {'HH','HV','entropy','alpha'} <= report['metrics'].keys():
        raise ValueError('This gallery requires HH/HV power and complex covariance descriptors.')
    paths = []
    for channel in ('HH','HV'):
        with rasterio.open(run/report['metrics'][channel]['file']) as ds:
            power = ds.read(1,masked=True).astype(float).filled(np.nan)
            bounds = ds.bounds
        db = 10*np.log10(power,out=np.full_like(power,np.nan),where=power>0)
        fig = Figure(figsize=(5,4.6),layout='constrained'); FigureCanvasAgg(fig)
        ax = fig.subplots()
        im = ax.imshow(db,cmap='gray',vmin=-25,vmax=5,interpolation='nearest',
                       extent=(bounds.left,bounds.right,bounds.bottom,bounds.top))
        ax.set_axis_off()
        fig.colorbar(im,ax=ax,orientation='horizontal',shrink=.85,label='Power (dB display)')
        path = run/f'{channel.lower()}.png'
        fig.savefig(path,dpi=dpi)
        paths.append(path)
    quad = len(report['channels']) == 4
    stem = run/('haalpha' if quad else 'halpha')
    (plot_haalpha if quad else plot_halpha)(run,output=stem,dpi=dpi)
    paths.append(stem.with_suffix('.png'))
    return paths
