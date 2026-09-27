import geopandas as gpd
import pytest
from shapely.geometry import Polygon, Point, box, mapping
from pynisar.aoi import read_aoi
from pynisar.discovery import search


class Granule:
    def __init__(self, geometry):
        self.__geo_interface__ = {'type':'Feature','geometry':mapping(geometry),'properties':{}}


class Client:
    def __init__(self, candidates):
        self.candidates=candidates

    def search_datasets(self, **kwargs):
        return [{'meta':{'concept-id':'C1'},'umm':{'ShortName':'NISAR_L2_GCOV'}}]

    def search_data(self, **kwargs):
        self.query=kwargs
        return self.candidates


@pytest.mark.parametrize('extension,driver',[('geojson','GeoJSON'),('gpkg','GPKG')])
def test_polygon_file_reprojection_and_hole_filter(tmp_path, extension, driver):
    polygon=Polygon([(0,0),(4,0),(4,4),(0,4)], holes=[[(1,1),(1,3),(3,3),(3,1)]])
    frame=gpd.GeoDataFrame(geometry=[polygon],crs=4326)
    if extension=='gpkg':
        frame=frame.to_crs(3857)
    path=tmp_path/f'aoi.{extension}'
    frame.to_file(path,driver=driver)
    read=read_aoi(path)
    assert read.crs.to_epsg()==4326
    assert read.geometry.iloc[0].area==pytest.approx(12)
    inside=Granule(box(.1,.1,.5,.5))
    hole=Granule(box(1.5,1.5,2,2))
    outside=Granule(box(5,5,6,6))
    client=Client([inside,hole,outside])
    result=search('C1',aoi=path,start='2025-11-01',end='2025-11-10',client=client)
    assert result==[inside]
    assert client.query['bounding_box']==pytest.approx((0,0,4,4))
    assert result.candidate_count==3 and not result.limit_reached


def test_gpkg_layer_must_be_explicit_when_multiple(tmp_path):
    path=tmp_path/'areas.gpkg'
    gpd.GeoDataFrame(geometry=[box(0,0,1,1)],crs=4326).to_file(path,layer='first',driver='GPKG')
    gpd.GeoDataFrame(geometry=[box(4,4,5,5)],crs=4326).to_file(path,layer='second',driver='GPKG')
    with pytest.raises(ValueError,match='Select a GeoPackage layer'):
        read_aoi(path)
    assert tuple(read_aoi(path,layer='second').total_bounds)==(4,4,5,5)


@pytest.mark.parametrize('geometry,crs',[(Point(0,0),4326),(box(0,0,1,1),None),
    (Polygon([(0,0),(1,1),(0,1),(1,0)]),4326),(box(-179,0,179,1),4326)])
def test_invalid_areas_rejected(geometry,crs):
    with pytest.raises(ValueError):
        read_aoi(gpd.GeoDataFrame(geometry=[geometry],crs=crs))


def test_limit_and_missing_footprint_are_disclosed():
    area=gpd.GeoDataFrame(geometry=[box(0,0,1,1)],crs=4326)
    with pytest.warns(UserWarning) as captured:
        result=search('C1',aoi=area,start='2025-11-01',end='2025-11-10',count=1,client=Client([object()]))
    assert len(captured)==2 and result.limit_reached and result.omitted_footprints==1
    assert not result


def test_choose_box_or_polygon_not_both():
    with pytest.raises(ValueError,match='exactly one'):
        search('C1',bbox=(0,0,1,1),aoi='anything.geojson',start='2025-11-01',end='2025-11-10')
