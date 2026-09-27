"""Reproject scientific layers before placing them on a web map."""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
from .display import _db, _limits
from .product_plots import POWER


def raster_overlay(path, *, metric, cmap='viridis'):
    """Return an RGBA web-Mercator preview, WGS84 bounds and the display scale."""
    from matplotlib import colormaps
    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise ValueError('Radar coordinates cannot be placed on a geographic map.')
        transform, width, height = calculate_default_transform(ds.crs, 'EPSG:3857', ds.width, ds.height, *ds.bounds)
        if width * height > 4_000_000:
            raise ValueError('Use a smaller subset for the web map.')
        values = np.full((height, width), np.nan, dtype='float32')
        reproject(source=ds.read(1, masked=True).astype('float32').filled(np.nan),
                  destination=values, src_transform=ds.transform, src_crs=ds.crs,
                  dst_transform=transform, dst_crs='EPSG:3857',
                  src_nodata=np.nan, dst_nodata=np.nan, resampling=Resampling.nearest)
    from rasterio.transform import array_bounds
    west, south, east, north = transform_bounds('EPSG:3857', 'EPSG:4326', *array_bounds(height, width, transform))
    shown = _db(values) if metric in POWER else values
    low, high = _limits(shown)
    normalized = np.clip((shown-low)/(high-low), 0, 1)
    rgba = colormaps[cmap](np.nan_to_num(normalized), bytes=True)
    rgba[..., 3] = np.where(np.isfinite(shown), 235, 0)
    return rgba, [[south, west], [north, east]], (low, high)


def product_map(path, *, metric, cmap='viridis'):
    import folium
    from folium.plugins import Fullscreen, MousePosition
    rgba, bounds, scale = raster_overlay(Path(path), metric=metric, cmap=cmap)
    center = np.mean(bounds, axis=0).tolist()
    map_ = folium.Map(location=center, tiles='OpenStreetMap', control_scale=True)
    folium.raster_layers.ImageOverlay(rgba, bounds=bounds, name=metric, opacity=1,
                                     interactive=True, cross_origin=False).add_to(map_)
    folium.LayerControl().add_to(map_)
    Fullscreen().add_to(map_); MousePosition().add_to(map_)
    map_.fit_bounds(bounds, padding=(35, 35))
    return map_, scale
