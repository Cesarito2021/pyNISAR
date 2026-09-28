"""Bounded NISAR discovery; Earthdata credentials stay with the caller."""
from datetime import date
import math
import warnings


def footprint(granule):
    """Read a catalogue polygon, including earthaccess versions on Python 3.11."""
    from shapely.geometry import shape, Polygon
    from shapely.ops import unary_union
    geo = getattr(granule, '__geo_interface__', None)
    if geo is not None:
        return shape(geo['geometry'] if geo.get('type') == 'Feature' else geo)
    polygons = granule['umm']['SpatialExtent']['HorizontalSpatialDomain']['Geometry']['GPolygons']
    def ring(boundary):
        return [(p['Longitude'], p['Latitude']) for p in boundary['Points']]
    result = unary_union([Polygon(ring(p['Boundary']),
        [ring(h) for h in p.get('ExclusiveZone', {}).get('Boundaries', [])])
        for p in polygons])
    return result


class SearchResults(list):
    """Granules plus the candidate limit and missing-footprint count."""
    def __init__(self, granules, *, candidate_count, limit, omitted_footprints=0):
        super().__init__(granules)
        self.candidate_count = candidate_count
        self.limit_reached = candidate_count >= limit
        self.omitted_footprints = omitted_footprints


def collections(*, client=None):
    if client is None:
        import earthaccess as client
    datasets = client.search_datasets(keyword='NISAR', count=100)
    return [dict(concept_id=d['meta']['concept-id'], short_name=d['umm']['ShortName'],
                 version=d['umm'].get('Version', ''), title=d['umm'].get('EntryTitle', ''))
            for d in datasets if 'NISAR' in d['umm']['ShortName'].upper()]


def search(concept_id, *, start, end, bbox=None, aoi=None, layer=None, count=20, client=None):
    """Find NISAR granules using a WGS84 box or polygon AOI.

    File AOIs query their bounding box, then intersect returned footprints with
    the exact polygon union (including holes). count limits candidates before
    polygon filtering; a limited query is not a complete inventory. Search
    selects whole granules, not a clipped HDF5 download or pixel mask.
    """
    if (bbox is None) == (aoi is None):
        raise ValueError('Provide exactly one of bbox or aoi.')
    boundary = None
    if aoi is not None:
        from .aoi import read_aoi
        frame = read_aoi(aoi, layer=layer)
        boundary = frame.geometry.union_all()
        bbox = frame.total_bounds.tolist()
    elif layer is not None:
        raise ValueError('layer applies only with a GeoPackage AOI.')
    if len(bbox) != 4 or not all(math.isfinite(v) for v in bbox):
        raise ValueError('bbox must contain four finite WGS84 coordinates.')
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError('Use west < east and south < north within WGS84 bounds.')
    if date.fromisoformat(str(start)) > date.fromisoformat(str(end)):
        raise ValueError('Start date must precede end date.')
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError('count must be an integer from 1 to 100.')
    if client is None:
        import earthaccess as client
    if concept_id not in {d['concept_id'] for d in collections(client=client)}:
        raise ValueError('Select a NISAR collection returned by collections().')
    candidates = client.search_data(concept_id=concept_id, bounding_box=tuple(bbox),
                                    temporal=(str(start), str(end)), count=count)
    matches, omitted = [], 0
    if boundary is None:
        matches = candidates
    else:
        from shapely.geometry import shape
        for granule in candidates:
            try:
                geometry = footprint(granule)
                if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon','MultiPolygon'):
                    raise ValueError('Unusable granule footprint.')
                if geometry.intersects(boundary):
                    matches.append(granule)
            except (ValueError, TypeError, KeyError, AttributeError):
                omitted += 1
    result = SearchResults(matches, candidate_count=len(candidates), limit=count, omitted_footprints=omitted)
    if result.limit_reached:
        warnings.warn('Candidate limit reached; narrow the area/dates or increase count. Results may be incomplete.', UserWarning)
    if omitted:
        warnings.warn(f'{omitted} candidates omitted because their footprints could not be verified.', UserWarning)
    return result
