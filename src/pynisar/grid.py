"""Shared raster alignment checks."""
import numpy as np

def check_raster_alignment(paths):
    """Reject unequal raster CRS, affine transforms or shapes; never resample.

    Equal grids are necessary but do not establish SLC coregistration or phase
    compatibility. Pixel-center/edge offsets are checked via the affine itself.
    """
    import rasterio
    paths = list(paths)
    if len(paths) < 2:
        raise ValueError('Provide at least two raster paths.')
    grids = []
    for path in paths:
        with rasterio.open(path) as ds:
            if ds.crs is None:
                raise ValueError(f'Missing map CRS: {path}')
            grids.append((ds.crs, ds.transform, ds.shape))
    if any(grid != grids[0] for grid in grids[1:]):
        raise ValueError('Raster grids differ: verify CRS, affine origin/resolution and shape.')
    return dict(common_grid=True, crs=str(grids[0][0]), shape=grids[0][2],
                coregistration_verified=False, phase_preparation_verified=False)
