import pytest
from pynisar.discovery import collections, search


class Client:
    def search_datasets(self, **kwargs):
        return [{'meta':{'concept-id':'C1'},'umm':{'ShortName':'NISAR_L2_GCOV','Version':'1'}},
                {'meta':{'concept-id':'C2'},'umm':{'ShortName':'OTHER'}}]

    def search_data(self, **kwargs):
        self.query=kwargs
        return ['measured-granule']


def test_search_passes_bounded_nisar_query():
    client=Client()
    assert len(collections(client=client))==1
    assert search('C1',bbox=(-91,46,-90,47),start='2025-11-01',end='2025-11-10',client=client)==['measured-granule']
    assert client.query['bounding_box']==(-91,46,-90,47)
    assert client.query['count']==20


@pytest.mark.parametrize('updates',[
    {'bbox':(-90,46,-91,47)}, {'bbox':(-190,46,-90,47)},
    {'start':'2025-12-01'}, {'concept_id':'C2'}, {'count':101},
])
def test_invalid_requests_rejected(updates):
    options=dict(concept_id='C1',bbox=(-91,46,-90,47),start='2025-11-01',end='2025-11-10',client=Client())
    options.update(updates)
    with pytest.raises(ValueError):
        search(**options)
