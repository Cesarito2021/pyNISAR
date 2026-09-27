"""One small, traceable analysis run per NISAR product and polarization mode."""
from pathlib import Path
import csv
import json
import uuid
import numpy as np
import rasterio
from affine import Affine

from .products import read_window
from .polarimetry import dualpol_metrics,intensity_metrics,_divide
from .quadpol import reciprocal_c3,quadpol_metrics
from .copol import copol_metrics

# A fixed 18-layer quad profile: measured channels are never duplicated as aliases.
QUAD_PROFILE = ('HH', 'HV', 'VH', 'VV', 'HV_reciprocal', 'span', 'entropy',
                'alpha', 'anisotropy', 'dop', 'rvi', 'prvi', 'pauli_odd',
                'pauli_double', 'pauli_cross', 'shannon_i', 'shannon_p',
                'reciprocity_residual')


def _derive(window, reciprocal):
    channels,cov = window.info['channels'],window.covariance
    if set(channels)=={'HH','HV','VH','VV'}:
        if not reciprocal:
            raise ValueError('Set reciprocal=True explicitly to form reciprocal C3 from measured HH/HV/VH/VV.')
        if cov is None:
            raise ValueError('Quad-pol C3 descriptors require all complex covariance terms.')
        c3 = reciprocal_c3(cov,channels)
        metrics = quadpol_metrics(c3)
        for p,a in window.intensity.items():
            metrics[p] = a
        i,j = channels.index('HV'),channels.index('VH')
        metrics['reciprocity_residual'] = _divide(cov[...,i,i].real+cov[...,j,j].real-2*cov[...,i,j].real,
                                                 cov[...,i,i].real+cov[...,j,j].real)
        return {name: metrics[name] for name in QUAD_PROFILE},c3,'reciprocal C3 / Pauli T3',[]
    if set(channels) in ({'HH','HV'},{'VV','VH'}):
        cp,xp = ('HH','HV') if 'HH' in channels else ('VV','VH')
        i,j = channels.index(cp),channels.index(xp)
        metrics = (dualpol_metrics(window.intensity[cp],window.intensity[xp],cov[...,i,j]) if cov is not None
                   else intensity_metrics(window.intensity[cp],window.intensity[xp]))
        metrics[cp],metrics[xp] = metrics.pop('HH'),metrics.pop('HV')
        skipped = [] if cov is not None else ['H, alpha, DoP, DpRVI, PRVI and Shannon: complex cross terms absent']
        return metrics,None,f'[{cp}, {xp}]',skipped
    if set(channels)=={'HH','VV'}:
        i,j = channels.index('HH'),channels.index('VV')
        metrics = copol_metrics(window.intensity['HH'],window.intensity['VV'],
                                cov[...,i,j] if cov is not None else None)
        skipped = [] if cov is not None else ['H, alpha, DoP and Pauli powers: complex cross terms absent']
        return metrics,None,'co-pol Pauli [(HH+VV)/sqrt(2), (HH-VV)/sqrt(2)]',skipped
    if len(channels)==1:
        return window.intensity.copy(),None,'single-pol intensity',['Polarimetric descriptors require additional channels']
    raise ValueError('Compact-pol and incomplete quad-pol interpretation require a separate validated method.')


def _save_array(path,a,window,description):
    if window.transform is None:
        row,col,_,_ = window.info['window']
        ly,lx = window.info['looks']
        affine = Affine(lx,0,col,0,ly,row)
    else:
        affine = window.transform
    with rasterio.open(path,'w',driver='GTiff',count=1,height=a.shape[0],width=a.shape[1],
                       dtype='float32',crs=window.crs,transform=affine,nodata=np.nan,compress='deflate') as dst:
        dst.write(a.astype('float32'),1)
        dst.set_band_description(1,description)
        dst.update_tags(geometry=window.info['geometry'],radiometry=window.info['radiometry'],
                        additional_correction='none',quantity=description)


def _save_matrix(run,c3,window):
    folder = run/'C3';folder.mkdir()
    for i in range(3):
        for j in range(i,3):
            a = c3[...,i,j]
            name = f'C{i+1}{j+1}'
            if i==j:
                _save_array(folder/f'{name}.tif',a.real,window,'C3: [HH,sqrt(2)*HV_reciprocal,VV]')
            else:
                _save_array(folder/f'{name}_real.tif',a.real,window,name+' real')
                _save_array(folder/f'{name}_imag.tif',a.imag,window,name+' imaginary')


def _statistics(a):
    v = a[np.isfinite(a)]
    return {'count':int(v.size),'finite_fraction':float(v.size/a.size),
            **{k:float(f(v)) if v.size else None for k,f in
               [('min',np.min),('median',np.median),('mean',np.mean),('max',np.max),('std',np.std)]}}


def analyze_product(source, output, *, reciprocal=False, **window_options):
    """Inspect/read a bounded GSLC/GCOV/RSLC window and export valid descriptors.

    Options are passed to read_window. Native H/A/alpha, Pauli powers, arithmetic,
    DoP and Shannon are available for reciprocal quad-pol. Advanced model-based
    decompositions are separate explicit calls. RSLC TIFFs have pixel coordinates
    and no map CRS; their panels are radar images, never geocoded map overlays.
    """
    window = read_window(source,**window_options)
    return _export_window(window, output, reciprocal=reciprocal)


def _export_window(window, output, *, reciprocal=False):
    """Export an already read window; also permits offline reproducibility checks."""
    metrics,c3,basis,skipped = _derive(window,reciprocal)
    run = Path(output)/('case-'+window.info['product'].lower()+'-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    report = dict(window.info,status='running',basis=basis,reciprocity_assumption=reciprocal,
                  implementation='pyNISAR native 0.1.0a1',metric_profile=('quad18' if c3 is not None else 'copol' if set(window.info['channels'])=={'HH','VV'} else 'single_intensity' if len(window.info['channels'])==1 else 'dual18_or_intensity10'),
                  metrics={},skipped=skipped)
    try:
        for name,a in metrics.items():
            _save_array(run/f'{name}.tif',a,window,name)
            report['metrics'][name] = dict(_statistics(a),file=f'{name}.tif',shape=list(a.shape))
        if window.covariance is not None:
            np.savez_compressed(run/'covariance.npz',covariance=window.covariance,channels=window.info['channels'])
        if c3 is not None:
            _save_matrix(run,c3,window)
        with (run/'statistics.csv').open('w',newline='',encoding='utf-8') as f:
            keys = ['metric','count','finite_fraction','min','median','mean','max','std']
            writer = csv.DictWriter(f,fieldnames=keys);writer.writeheader()
            for name,info in report['metrics'].items():
                writer.writerow(dict(metric=name,**{k:info[k] for k in keys[1:]}))
        report['status'] = 'complete'
    except Exception as exc:
        report.update(status='failed',error=str(exc))
        raise
    finally:
        (run/'manifest.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
    return run
