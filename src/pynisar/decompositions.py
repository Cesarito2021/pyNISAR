"""Explicit, isolated access to the predecessor's PolSARtools decompositions."""
from pathlib import Path
import importlib.metadata
import json
import shutil
import uuid
import numpy as np
import rasterio
from .quadpol import quadpol_metrics

QUAD_METHODS = {
    'h_a_alpha_fp': ['H_fp.tif','alpha_fp.tif','anisotropy_fp.tif'],
    'mf3cf': ['Ps_mf3cf.tif','Pd_mf3cf.tif','Pv_mf3cf.tif','Theta_FP_mf3cf.tif'],
    'yamaguchi_4c': ['Yam4co_odd.tif','Yam4co_dbl.tif','Yam4co_vol.tif','Yam4co_hlx.tif'],
    'dop_fp': ['dop_fp.tif'],
    'shannon_h_fp': ['H_Shannon.tif','HI_Shannon.tif','HP_Shannon.tif'],
}
INTENSITY_METHODS = {
    'dprvic': ['dprvic.tif'],
    'dp_desc': ['mc.tif','Hc.tif','Thetac.tif'],
    'powers_dp_grd': ['Alpha_dp_grd.tif','Psl_dcmp_grd.tif','Pdl_dcmp_grd.tif','Pu_dcmp_grd.tif'],
    'powers_dp_grd_factor': ['Psl_fact_grd.tif','Pdl_fact_grd.tif','Pr_fact_grd.tif'],
}


def _backend():
    try:
        version=importlib.metadata.version('polsartools')
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError('Install pynisar[decompositions] in a GDAL-compatible environment.') from exc
    if version!='0.11':
        raise RuntimeError('This predecessor adapter requires PolSARtools 0.11; other versions need validation.')
    import polsartools
    return polsartools,version


def _inputs(run,folder,report):
    if (run/'C3').is_dir():
        shutil.copytree(run/'C3',folder)
        return [str(folder)],QUAD_METHODS
    channels=set(report['channels'])
    if channels not in ({'HH','HV'},{'VV','VH'}):
        raise ValueError('Expected reciprocal C3 or dual co/cross-pol powers.')
    cp,xp=('HH','HV') if 'HH' in channels else ('VV','VH')
    folder.mkdir()
    for channel in (cp,xp):
        shutil.copy2(run/report['metrics'][channel]['file'],folder/f'{channel}.tif')
    return [str(folder/f'{cp}.tif'),str(folder/f'{xp}.tif')],INTENSITY_METHODS


def _verify_outputs(folder,files):
    result={}
    for name in files:
        path=folder/name
        if not path.is_file():raise RuntimeError(f'Decomposition did not produce {name}.')
        with rasterio.open(path) as ds:
            a=ds.read(1,masked=True).filled(np.nan)
        count=int(np.isfinite(a).sum())
        if count==0:raise RuntimeError(f'Decomposition output {name} has no finite samples.')
        result[name]={'finite_count':count,'total_count':int(a.size)}
    return result


def _smoothed_matrix(folder, window):
    from scipy.ndimage import uniform_filter
    matrix = None
    for i in range(3):
        for j in range(i,3):
            name=f'C{i+1}{j+1}'
            with rasterio.open(folder/(name+'.tif' if i==j else name+'_real.tif')) as ds:
                a=ds.read(1).astype('complex128')
                if matrix is None: matrix=np.empty(a.shape+(3,3),complex)
            if i!=j:
                with rasterio.open(folder/(name+'_imag.tif')) as ds:a+=1j*ds.read(1)
            matrix[...,i,j],matrix[...,j,i]=a,a.conj()
    valid=np.isfinite(matrix).all(axis=(-2,-1))
    for i in range(3):
        for j in range(3):
            a=np.where(valid,matrix[...,i,j],0)
            matrix[...,i,j]=uniform_filter(a.real,size=window,mode='constant')+1j*uniform_filter(a.imag,size=window,mode='constant')
    return matrix


def _native_descriptors(folder, method, window):
    """Avoid known 0.11 eigenvector-indexing and absolute-epsilon issues."""
    values=quadpol_metrics(_smoothed_matrix(folder,window))
    keys=['entropy','alpha','anisotropy'] if method=='h_a_alpha_fp' else ['shannon','shannon_i','shannon_p']
    with rasterio.open(folder/'C11.tif') as ds:profile=ds.profile
    for key,name in zip(keys,QUAD_METHODS[method]):
        with rasterio.open(folder/name,'w',**profile) as dst:dst.write(values[key].astype('float32'),1)


def _mask_outputs(folder, files, args, window):
    """Exclude incomplete support and upstream block-writer edge padding."""
    from scipy.ndimage import binary_erosion
    inputs=list(folder.glob('C*.tif')) if len(args)==1 else [Path(p) for p in args]
    valid=None
    for path in inputs:
        with rasterio.open(path) as ds:a=ds.read(1)
        valid=np.isfinite(a) if valid is None else valid & np.isfinite(a)
    power_inputs=[folder/f'C{i}{i}.tif' for i in (1,2,3)] if len(args)==1 else inputs
    total=np.zeros(valid.shape)
    for path in power_inputs:
        with rasterio.open(path) as ds:total+=ds.read(1)
    valid &= total>0
    valid=binary_erosion(valid,structure=np.ones((2*window+1,2*window+1)))
    for name in files:
        with rasterio.open(folder/name,'r+') as ds:
            a=ds.read(1);a[~valid]=np.nan;ds.write(a,1);ds.nodata=np.nan
            ds.update_tags(excluded_border_pixels=window,validity='common finite input support')


def decompose(run, *, methods=None, window=3, allow_experimental=False):
    """Run selected predecessor algorithms on a copy of a bounded analysis output.

    Supported quad-pol methods: h_a_alpha_fp, mf3cf, yamaguchi_4c, dop_fp,
    shannon_h_fp. Intensity-only methods: dprvic, dp_desc, powers_dp_grd,
    powers_dp_grd_factor. The latter are intensity-based approximations, not
    substitutes for complex-covariance descriptors. Errors are never swallowed.
    The native analysis remains intact in its original directory.
    H/A/alpha and Shannon use native corrected formulas with matched boxcar support.
    Yamaguchi is excluded by default and requires allow_experimental=True because
    upstream output powers did not close to span in the real validation windows.
    """
    if type(window) is not int or window<1 or window%2!=1:
        raise ValueError('window must be a positive odd integer.')
    run=Path(run)
    report=json.loads((run/'manifest.json').read_text())
    if report['status']!='complete':raise ValueError('A completed analyze_product run is required.')
    available=QUAD_METHODS if (run/'C3').is_dir() else INTENSITY_METHODS
    methods=list(methods) if methods is not None else [m for m in available if m!='yamaguchi_4c']
    if not methods or not set(methods)<=available.keys():raise ValueError('Choose supported decomposition methods for this input.')
    if 'yamaguchi_4c' in methods and not allow_experimental:
        raise ValueError('Yamaguchi 0.11 showed 4.6–7.6% maximum span closure errors in real cases. Set allow_experimental=True only to inspect this upstream method.')
    backend,version=_backend()
    target=run/('decompositions-'+uuid.uuid4().hex);target.mkdir()
    folder=target/'input'
    state={'status':'running','backend':'polsartools','version':version,'window':window,
           'source_run':str(run),'methods':methods,'outputs':{},'filter':'boxcar within each function; no Refined Lee',
           'native_overrides':['h_a_alpha_fp','shannon_h_fp'], 'excluded_border_pixels':window,
           'experimental': 'yamaguchi_4c' in methods,
           'validation_note':'Native Hermitian H/A/alpha and scale-consistent Shannon replace known upstream 0.11 issues. Yamaguchi is experimental, not independently validated.'}
    try:
        args,_=_inputs(run,folder,report)
        for method in methods:
            name='powers_dp_grd' if method=='powers_dp_grd_factor' else method
            kwargs={'win':window,'fmt':'tif','max_workers':1,'block_size':(512,512)}
            if method=='powers_dp_grd_factor':kwargs['method']=2
            if method=='yamaguchi_4c':kwargs['model']=''
            if method in ('h_a_alpha_fp','shannon_h_fp'):
                _native_descriptors(folder,method,window)
            else:
                getattr(backend,name)(*args,**kwargs)
            _mask_outputs(folder,available[method],args,window)
            state['outputs'][method]=_verify_outputs(folder,available[method])
        state['status']='complete'
    except Exception as exc:
        state.update(status='failed',error=str(exc));raise
    finally:
        (target/'manifest.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
    return target
