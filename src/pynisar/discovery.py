"""Bounded NISAR discovery; Earthdata credentials stay with the caller."""
from datetime import date
import math


def collections(*, client=None):
    if client is None:
        import earthaccess as client
    datasets = client.search_datasets(keyword='NISAR', count=100)
    return [dict(concept_id=d['meta']['concept-id'], short_name=d['umm']['ShortName'],
                 version=d['umm'].get('Version', ''), title=d['umm'].get('EntryTitle', ''))
            for d in datasets if 'NISAR' in d['umm']['ShortName'].upper()]


def search(concept_id, *, bbox, start, end, count=20, client=None):
    """Return earthaccess granules from a verified NISAR collection and WGS84 bbox."""
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
    return client.search_data(concept_id=concept_id, bounding_box=tuple(bbox),
                              temporal=(str(start), str(end)), count=count)
