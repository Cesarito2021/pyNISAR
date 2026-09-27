"""Metadata-led, bounded readers for NISAR GSLC, GCOV and RSLC products."""
from dataclasses import dataclass
import h5py
import numpy as np
import rasterio
from affine import Affine

from .backscatter import _window, _validate, _complex_window
from .polarimetry import _mean_blocks

CHANNELS = ('HH', 'HV', 'VH', 'VV', 'RH', 'RV', 'LH', 'LV')


def _group(h, frequency):
    if frequency not in ('A', 'B'):
        raise ValueError('frequency must be A or B.')
    products = [p for p in ('GSLC', 'GCOV', 'RSLC') if f'/science/LSAR/{p}' in h]
    if len(products) != 1:
        raise ValueError('Expected exactly one L-band GSLC, GCOV or RSLC product.')
    product = products[0]
    geometry = 'swaths' if product == 'RSLC' else 'grids'
    path = f'/science/LSAR/{product}/{geometry}/frequency{frequency}'
    if path not in h:
        raise ValueError(f'frequency{frequency} is absent from {product}.')
    return product, h[path]


def _channels(g, product):
    suffix = 2 if product == 'GCOV' else 1
    channels = [p for p in CHANNELS if p*suffix in g]
    if not channels:
        raise ValueError('No recognized polarization datasets.')
    return channels


def inspect_product(source, *, frequency='A'):
    """Inspect actual HDF5 datasets, independently of filenames and pol codes."""
    with h5py.File(source, 'r') as h:
        product, g = _group(h, frequency)
        channels = _channels(g, product)
        terms = [k for k in g if len(k) == 4 and k[:2] in channels and k[2:] in channels]
        offdiag = [k for k in terms if k[:2] != k[2:]]
        mode = 'quad' if set(('HH','HV','VH','VV')) <= set(channels) else 'dual' if len(channels) == 2 else 'single' if len(channels) == 1 else 'other'
        return {'product': product, 'frequency': frequency, 'channels': channels, 'mode': mode,
                'geometry': 'radar' if product == 'RSLC' else 'map', 'covariance_terms': terms,
                'off_diagonal_available': product != 'GCOV' or bool(offdiag),
                'datasets': {p: {'shape': list(g[p*2 if product == 'GCOV' else p].shape),
                                'dtype': str(g[p*2 if product == 'GCOV' else p].dtype)} for p in channels}}


@dataclass
class ProductWindow:
    info: dict
    intensity: dict
    covariance: np.ndarray | None
    transform: object = None
    crs: object = None


def _selection(g, product, center, pixel, size, looks, shape):
    if center is not None and pixel is not None:
        raise ValueError('Choose geographic center or radar pixel, not both.')
    if product == 'RSLC':
        if center is not None:
            raise ValueError('RSLC is in radar geometry; use pixel=(row, column), not longitude/latitude.')
        row, col = pixel if pixel is not None else (shape[0]//2, shape[1]//2)
        if any(type(v) is not int for v in (row, col)) or not (0 <= row < shape[0] and 0 <= col < shape[1]):
            raise ValueError('Radar pixel must be an in-bounds integer row/column pair.')
        nr, nc = [min(size, n)//l*l for n, l in zip(shape, looks)]
        if not nr or not nc:
            raise ValueError('Window is smaller than the selected looks.')
        r, c = max(0, min(row-nr//2, shape[0]-nr)), max(0, min(col-nc//2, shape[1]-nc))
        return [r,c,nr,nc], None, None
    if pixel is not None:
        raise ValueError('Map products use center=(longitude, latitude).')
    x, y = np.asarray(g['xCoordinates']), np.asarray(g['yCoordinates'])
    dx, dy = float(g['xCoordinateSpacing'][()]), float(g['yCoordinateSpacing'][()])
    if shape != (len(y), len(x)) or dx == 0 or dy == 0:
        raise ValueError('Inconsistent map coordinates or raster shape.')
    if not np.allclose(np.diff(x), dx) or not np.allclose(np.diff(y), dy):
        raise ValueError('Nonuniform map coordinates.')
    crs = rasterio.crs.CRS.from_epsg(int(g['projection'][()]))
    window, affine = _window(center, size, looks, x, y, dx, dy, crs)
    return window, affine, crs


def _gcov(g, channels, window, looks, shape):
    r, c, nr, nc = window
    components = {}
    complete = True
    for i, p in enumerate(channels):
        for j in range(i, len(channels)):
            q = channels[j]
            name, conjugate = (p+q, False) if p+q in g else (q+p, True)
            if name not in g:
                complete = False
                continue
            ds = g[name]
            if ds.shape != shape:
                raise ValueError('GCOV component shapes differ.')
            if i == j:
                a = ds[r:r+nr,c:c+nc].astype('float64')
            else:
                a = _complex_window(ds, window, shape).astype('complex128')
                if conjugate:
                    a = a.conj()
            components[i,j] = a
    valid = np.logical_and.reduce([np.isfinite(a) for a in components.values()])
    components = {k:_mean_blocks(np.where(valid,a,np.nan),looks) for k,a in components.items()}
    powers = {p:components[i,i].real for i,p in enumerate(channels)}
    if not complete:
        return powers, None
    cov = np.empty(next(iter(powers.values())).shape+(len(channels),len(channels)), complex)
    for (i,j), a in components.items():
        cov[...,i,j], cov[...,j,i] = a, a.conj()
    return powers, cov


def _slc(g, channels, window, looks, shape):
    samples = [_complex_window(g[p],window,shape).astype('complex128') for p in channels]
    valid = np.logical_and.reduce([np.isfinite(a) for a in samples])
    samples = [np.where(valid,a,np.nan) for a in samples]
    nr, nc = window[2:]
    cov = np.empty((nr//looks[0],nc//looks[1],len(channels),len(channels)), complex)
    for i, a in enumerate(samples):
        for j in range(i,len(samples)):
            cov[...,i,j] = _mean_blocks(a*samples[j].conj(),looks)
            cov[...,j,i] = cov[...,i,j].conj()
    return {p:cov[...,i,i].real for i,p in enumerate(channels)}, cov


def read_window(source, *, frequency='A', channels=None, center=None, pixel=None,
                window_size=256, looks=(1,1)):
    """Read a small native product window. RSLC never receives a fabricated map CRS.

    GCOV covariance is preserved as supplied; absent cross terms stay absent.
    Additional GCOV looks average stored covariance, not complex amplitudes.
    Compact-pol datasets can be inspected/read but are not interpreted as HH/HV.
    """
    # Validate numeric options independently of the selected sensor channels.
    _validate(('HH',),window_size,looks)
    with h5py.File(source,'r') as h:
        product,g = _group(h,frequency)
        available = _channels(g,product)
        channels = list(channels) if channels is not None else available
        if not channels or len(channels)!=len(set(channels)) or not set(channels)<=set(available):
            raise ValueError('Requested distinct channels are not present in this frequency.')
        shape = g[channels[0]*2 if product=='GCOV' else channels[0]].shape
        window,affine,crs = _selection(g,product,center,pixel,window_size,looks,shape)
        powers,cov = (_gcov if product=='GCOV' else _slc)(g,channels,window,looks,shape)
    info = {'product':product,'frequency':frequency,'channels':channels,'window':window,
            'looks':list(looks),'geometry':'radar' if product=='RSLC' else 'map',
            'crs':str(crs) if crs else None,'center_lonlat':center,'radar_pixel':pixel,
            'source':getattr(source,'url',str(source)),
            'radiometry':'as-stored GCOV (nominal gamma0)' if product=='GCOV' else 'uncorrected mean |S|^2',
            'additional_radiometric_correction':False,'filter':'boxcar_only',
            'covariance_complete':cov is not None}
    if hasattr(source,'bytes_read'):
        info['response_body_bytes_read'] = source.bytes_read
    return ProductWindow(info,powers,cov,affine,crs)
