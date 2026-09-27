"""Measured, already multilooked NISAR subsets used by the original gallery."""
from importlib.resources import files
import json
import numpy as np
import rasterio
from .products import ProductWindow
from .analysis import _export_window


def sample(mode='dual'):
    """Load a real bundled subset; preserve its original support and radiometry."""
    if mode not in ('dual', 'quad'):
        raise ValueError('mode must be dual or quad.')
    folder = files('pynisar').joinpath('data', mode)
    original = json.loads(folder.joinpath('manifest.json').read_text(encoding='utf-8'))
    keys = ('product', 'frequency', 'channels', 'window', 'looks', 'geometry', 'crs',
            'center_lonlat', 'radar_pixel', 'source', 'radiometry',
            'additional_radiometric_correction', 'filter', 'covariance_complete', 'channel_selection')
    info = {k: original[k] for k in keys if k in original}
    info['sample_provenance'] = 'Measured 2025-11-06 western Great Lakes subset inherited from PyGeoObserver'
    info['sample_processing'] = 'Descriptors recomputed from stored multilooked covariance; no additional looks'
    intensity = {}
    for channel in info['channels']:
        with rasterio.open(str(folder.joinpath(channel + '.tif'))) as ds:
            intensity[channel] = ds.read(1, masked=True).astype(float).filled(np.nan)
            transform, crs = ds.transform, ds.crs
    with folder.joinpath('covariance.npz').open('rb') as stream:
        with np.load(stream, allow_pickle=False) as archive:
            covariance = archive['covariance'].copy()
            if list(archive['channels']) != info['channels']:
                raise ValueError('Sample channel order does not match its manifest.')
    return ProductWindow(info, intensity, covariance, transform, crs)


def process_sample(output, *, mode='dual'):
    """Recompute products from a measured subset, without NASA authentication."""
    return _export_window(sample(mode), output, reciprocal=(mode == 'quad'))
