"""HH/VV descriptors in the two-component Pauli basis; no cross-pol inference."""
import numpy as np
from .polarimetry import _divide, _eigen_metrics


def copol_metrics(hh, vv, cross=None):
    """Powers and, when available, H/alpha from <HH VV*>.

    Basis: [(HH+VV)/sqrt(2), (HH-VV)/sqrt(2)]. Entropy uses log2.
    Alpha is undefined for equal eigenvalues; this is not full-pol H/alpha.
    """
    a, b = np.asarray(hh, float), np.asarray(vv, float)
    if a.shape != b.shape or np.any(a < 0) or np.any(b < 0):
        raise ValueError('HH and VV powers must have equal shapes and be nonnegative.')
    result = dict(HH=a, VV=b, copol_span=a+b, HH_VV_ratio=_divide(a, b))
    if cross is None:
        return result
    z = np.asarray(cross, complex)
    if z.shape != a.shape:
        raise ValueError('Cross covariance must have the same shape as powers.')
    # Validate the original C2 before rotating it into the Pauli basis.
    _eigen_metrics(a, b, z)
    odd, double = (a+b+2*z.real)/2, (a+b-2*z.real)/2
    t12 = (a-b)/2-1j*z.imag
    eig = _eigen_metrics(odd, double, t12)
    alpha = np.where(eig['dop'] > 1e-10, eig['alpha'], np.nan)
    result.update(entropy=eig['entropy'], alpha=alpha, dop=eig['dop'],
                  copol_odd=np.maximum(odd, 0), copol_double=np.maximum(double, 0))
    return result
