"""Reciprocal C3 and Pauli T3 descriptors from measured four-channel covariance."""
import numpy as np
from .polarimetry import _divide, _log


def reciprocal_c3(covariance, channels):
    """Apply [HH, (HV+VH)/sqrt(2), VV], retaining coherent cross-pol averaging."""
    if set(channels) != {'HH','HV','VH','VV'} or covariance.shape[-2:] != (4,4):
        raise ValueError('Reciprocal C3 requires measured HH, HV, VH and VV covariance.')
    matrix = np.zeros((3,4))
    matrix[0,channels.index('HH')] = 1
    matrix[1,channels.index('HV')] = matrix[1,channels.index('VH')] = 1/np.sqrt(2)
    matrix[2,channels.index('VV')] = 1
    return matrix @ covariance @ matrix.T


def _eigen(c3):
    pauli = np.array([[1,0,1],[1,0,-1],[0,np.sqrt(2),0]])/np.sqrt(2)
    t3 = pauli @ c3 @ pauli.T
    span = np.trace(t3,axis1=-2,axis2=-1).real
    valid = np.isfinite(t3).all(axis=(-2,-1)) & (span>0)
    values,vectors = np.linalg.eigh(np.where(valid[...,None,None],t3,0))
    if np.any(values[...,0][valid] < -1e-6*span[valid]):
        raise ValueError('Quad-pol covariance is not positive semidefinite.')
    values = np.maximum(values[...,::-1],0)
    vectors = vectors[...,::-1]
    p = _divide(values,values.sum(axis=-1,keepdims=True))
    entropy = -(p*np.log(p,out=np.zeros_like(p),where=p>0)).sum(axis=-1)/np.log(3)
    alpha = (p*np.degrees(np.arccos(np.clip(np.abs(vectors[...,0,:]),0,1)))).sum(axis=-1)
    # Positive repeated eigenvalues do not uniquely identify their eigenvectors.
    repeated = np.any((np.abs(np.diff(values,axis=-1)) < 1e-10*span[...,None]) & (values[...,1:] > 1e-10*span[...,None]),axis=-1)
    alpha = np.where(repeated,np.nan,alpha)
    anisotropy = _divide(values[...,1]-values[...,2],values[...,1]+values[...,2])
    determinant_fraction = 27*np.prod(p,axis=-1)
    dop = np.sqrt(np.clip(1-determinant_fraction,0,1))
    hi,hp = 3*_log(np.pi*np.e*span/3),_log(determinant_fraction)
    return {'entropy':entropy,'alpha':alpha,'anisotropy':anisotropy,'dop':dop,
            'e1':p[...,0],'e2':p[...,1],'e3':p[...,2], 'shannon':hi+hp,
            'shannon_i':hi,'shannon_p':hp,'pauli_odd':t3[...,0,0].real,
            'pauli_double':t3[...,1,1].real,'pauli_cross':t3[...,2,2].real}


def quadpol_metrics(c3):
    """Full-pol descriptors with C22=2*reciprocal HV power, not HV power.

    C3 basis must be [HH, sqrt(2)*HV_reciprocal, VV]. This fixes the
    cross-pol scaling ambiguity in the original library's full-pol branch.
    H/alpha use the Pauli T3 basis and log(3), unlike dual-pol descriptors.
    """
    c3 = np.asarray(c3,complex)
    if c3.shape[-2:] != (3,3):
        raise ValueError('Expected a 3 by 3 covariance matrix per pixel.')
    if not np.allclose(c3,np.swapaxes(c3.conj(),-1,-2),equal_nan=True):
        raise ValueError('C3 must be Hermitian.')
    hh,hv,vv = c3[...,0,0].real,c3[...,1,1].real/2,c3[...,2,2].real
    span = hh+2*hv+vv
    layers = {'HH':hh,'HV_reciprocal':hv,'VV':vv,'span':span,
              'rvi':_divide(8*hv,span),'HH_fraction':_divide(hh,span),
              'HV_fraction':_divide(hv,span),'VV_fraction':_divide(vv,span),
              'HH_VV_ratio':_divide(hh,vv),'cpr':_divide(hv,hh),
              'ndsi':_divide(hh-hv,hh+hv),'product':hh*hv,'sum_HH_HV':hh+hv}
    layers.update(_eigen(c3))
    layers['prvi'] = (1-layers['dop'])*hv
    return layers
