"""Shared scientific display transforms."""
import numpy as np

def _db(a):
    return 10*np.log10(a, out=np.full_like(a, np.nan), where=a > 0)


def _limits(a):
    values = a[np.isfinite(a)]
    if not values.size:
        return 0., 1.
    lo, hi = np.percentile(values, [2, 98])
    return float(lo), float(hi if hi > lo else lo+1)
