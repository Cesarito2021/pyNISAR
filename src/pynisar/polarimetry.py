"""Small-window dual-pol descriptors in the explicit [HH, HV] C2 basis.

No radiometric correction, noise subtraction, or Refined Lee is implied.
See docs/POLARIMETRY.md for equations, units, references and limitations.
"""
from pathlib import Path
import csv
import json
import uuid

import h5py
import numpy as np
import rasterio

from .backscatter import _validate, _grid, _window, _complex_window


def _mean_blocks(a, looks):
    rows, cols = a.shape
    return a.reshape(rows//looks[0], looks[0], cols//looks[1], looks[1]).mean(axis=(1, 3))


def _covariance(hh, hv, looks):
    # A common sample mask preserves positive semidefiniteness of C2.
    valid = np.isfinite(hh) & np.isfinite(hv)
    hh = np.where(valid, hh, np.nan).astype('complex128')
    hv = np.where(valid, hv, np.nan).astype('complex128')
    a = _mean_blocks(np.abs(hh)**2, looks)
    b = _mean_blocks(np.abs(hv)**2, looks)
    z = _mean_blocks(hh*np.conj(hv), looks)
    return a, b, z


def _divide(a, b):
    result = np.full(np.broadcast_shapes(np.shape(a), np.shape(b)), np.nan)
    return np.divide(a, b, out=result, where=np.isfinite(b) & (b > 0))


def _log(a):
    return np.log(a, out=np.full_like(a, np.nan, dtype=float), where=a > 0)


def _eigen_metrics(a, b, z):
    c = np.empty(a.shape+(2, 2), dtype='complex128')
    c[..., 0, 0], c[..., 1, 1] = a, b
    c[..., 0, 1], c[..., 1, 0] = z, z.conj()
    valid = np.isfinite(c).all(axis=(-2, -1)) & (a+b > 0)
    values, vectors = np.linalg.eigh(np.where(valid[..., None, None], c, 0))
    if np.any(values[..., 0][valid] < -1e-10*(a+b)[valid]):
        raise ValueError('C2 is not positive semidefinite.')
    values = np.maximum(values, 0)
    p = _divide(values, values.sum(axis=-1, keepdims=True))
    logp = np.log2(p, out=np.zeros_like(p), where=p > 0)
    entropy = -(p*logp).sum(axis=-1)
    angles = np.degrees(np.arccos(np.clip(np.abs(vectors[..., 0, :]), 0, 1)))
    alpha = (p*angles).sum(axis=-1)
    dop = p[..., 1]-p[..., 0]
    return {'entropy': entropy, 'alpha': alpha, 'dop': dop,
            'dprvi': 1-dop*p[..., 1], 'prvi': (1-dop)*b}


def intensity_metrics(a, b):
    """Ten arithmetic HH/HV descriptors; no phase-derived quantities are inferred."""
    a,b = np.asarray(a,float),np.asarray(b,float)
    if a.shape != b.shape or np.any(a < 0) or np.any(b < 0):
        raise ValueError('Intensity inputs must have equal shapes and nonnegative powers.')
    span = a+b
    return {'HH': a, 'HV': b, 'span': span, 'ratio': _divide(a,b),
            'cpr': _divide(b,a), 'difference': a-b, 'product': a*b,
            'fraction': _divide(b,span), 'ndsi': _divide(a-b,span), 'rvi': _divide(4*b,span)}


def dualpol_metrics(a, b, z):
    """Derive arrays from C11, C22 and complex C12; basis is [HH, HV].

    Inputs must share a shape. Zero denominators produce NaN, not epsilon-biased
    ratios. Zero-power pixels have undefined normalized descriptors. Singular
    C2 pixels have undefined finite Shannon differential entropy (stored NaN).
    """
    a, b, z = np.asarray(a, float), np.asarray(b, float), np.asarray(z, complex)
    if a.shape != b.shape or a.shape != z.shape:
        raise ValueError('C2 components must have identical shapes.')
    if np.any(a < 0) or np.any(b < 0):
        raise ValueError('C2 diagonal powers cannot be negative.')
    span = a+b
    layers = intensity_metrics(a,b)
    layers.update(_eigen_metrics(a, b, z))
    determinant = a*b-np.abs(z)**2
    hi = 2*_log(np.pi*np.e*span/2)
    hp = _log(_divide(4*determinant, span**2))
    layers.update(shannon=hi+hp, shannon_i=hi, shannon_p=hp)
    return layers


def _write_metric(run, name, data, crs, affine):
    file = f'intensity_{name}.tif' if name in ('HH', 'HV') else f'{name}.tif'
    with rasterio.open(run/file, 'w', driver='GTiff', count=1, dtype='float32',
                       height=data.shape[0], width=data.shape[1], crs=crs,
                       transform=affine, nodata=np.nan, compress='deflate') as dst:
        dst.write(data.astype('float32'), 1)
        dst.set_band_description(1, name)
        dst.update_tags(basis='HH,HV', radiometric_correction='none', filter='boxcar',
                        equations='pyNISAR docs/POLARIMETRY.md')
    finite = data[np.isfinite(data)]
    return {'file': file, 'shape': list(data.shape), 'count': int(finite.size),
            'finite_fraction': float(finite.size/data.size),
            **{key: float(fun(finite)) if finite.size else None for key, fun in
               [('min', np.min), ('median', np.median), ('mean', np.mean), ('max', np.max), ('std', np.std)]}}


def analyze_gslc(source, output, *, center=None, window_size=512, looks=(6, 3)):
    """Read one bounded HH/HV complex window and export 18 dual-pol descriptors.

    Uses nonoverlapping boxcar C2 multilooks and native NumPy eigendecomposition.
    This is a documented new implementation, not a reproduction of the legacy
    PolSARtools/Refined-Lee pipeline. Returns a unique directory with provenance.
    """
    _validate(('HH', 'HV'), window_size, looks)
    with h5py.File(source, 'r') as h:
        g, x, y, dx, dy, crs = _grid(h, ('HH', 'HV'))
        window, affine = _window(center, window_size, looks, x, y, dx, dy, crs)
        hh, hv = [_complex_window(g[c], window, (len(y), len(x))) for c in ('HH', 'HV')]
    a, b, z = _covariance(hh, hv, looks)
    layers = dualpol_metrics(a, b, z)
    run = Path(output)/('dualpol-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    report = {'status': 'running', 'source': str(source), 'window': window, 'looks': list(looks),
              'center_lonlat': center, 'channels': ['HH', 'HV'], 'basis': '[HH, HV]',
              'radiometric_correction': False, 'filter': 'boxcar_multilook_only',
              'shannon_log_base': 'e', 'implementation': 'pyNISAR native C2 v1',
              'crs': str(crs), 'pixel_size_m': [abs(affine.a), abs(affine.e)], 'metrics': {}}
    try:
        # Preserve the small covariance arrays for independent numerical checks.
        np.savez_compressed(run/'covariance.npz', c11=a, c22=b, c12=z)
        for name, data in layers.items():
            report['metrics'][name] = _write_metric(run, name, data, crs, affine)
        report['layers'] = {c: report['metrics'][c] for c in ('HH', 'HV')}
        with (run/'statistics.csv').open('w', newline='', encoding='utf-8') as f:
            keys = ['metric', 'count', 'finite_fraction', 'min', 'median', 'mean', 'max', 'std']
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for name, info in report['metrics'].items():
                writer.writerow({'metric': name, **{k: info[k] for k in keys[1:]}})
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed', error=str(exc))
        raise
    finally:
        (run/'manifest.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    return run
