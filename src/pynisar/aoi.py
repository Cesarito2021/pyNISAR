"""Polygon AOIs adapted from PyGeoObserver; normalize declared CRS to WGS84."""
from pathlib import Path


def read_aoi(source, *, layer=None):
    """Read a local GeoJSON/GPKG or GeoDataFrame with valid polygon boundaries.

    Select a layer explicitly for multi-layer GeoPackages. Geographic coordinates
    follow GeoJSON's WGS84 convention; other inputs must declare their CRS.
    """
    import geopandas as gpd
    if isinstance(source, gpd.GeoDataFrame):
        if layer is not None:
            raise ValueError('layer applies only to a GeoPackage file.')
        frame = source.copy()
    else:
        path = Path(source)
        if not path.is_file() or path.suffix.lower() not in ('.geojson', '.json', '.gpkg'):
            raise ValueError('Select a local GeoJSON or GeoPackage polygon file.')
        if path.suffix.lower() == '.gpkg':
            names = gpd.list_layers(path)['name'].tolist()
            if layer is None and len(names) != 1:
                raise ValueError('Select a GeoPackage layer: '+', '.join(names))
            if layer is not None and layer not in names:
                raise ValueError('Unknown GeoPackage layer: '+str(layer))
            frame = gpd.read_file(path, layer=layer or names[0])
        else:
            if layer is not None:
                raise ValueError('layer applies only to a GeoPackage file.')
            frame = gpd.read_file(path)
    if frame.empty or frame.crs is None:
        raise ValueError('AOI must contain polygons and declare its CRS.')
    geometry = frame.geometry
    if geometry.isna().any() or geometry.is_empty.any() or not geometry.is_valid.all():
        raise ValueError('AOI contains missing, empty or invalid geometries.')
    if not frame.geom_type.isin(['Polygon', 'MultiPolygon']).all():
        raise ValueError('Use Polygon or MultiPolygon boundaries, not points or lines.')
    frame = frame.to_crs(4326)
    west, south, east, north = frame.total_bounds
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90) or east-west > 180:
        raise ValueError('Invalid bounds or antimeridian-crossing AOI; split it before searching.')
    return frame[['geometry']]
