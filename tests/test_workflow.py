import json
import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import box
from test_products import fixture
from pynisar.workflow import square_aoi, process_area, scene_table


def test_square_is_five_km_in_projected_space():
    area = square_aoi(-90.2, 46.45).to_crs(32615)
    assert area.geometry.area.iloc[0] == pytest.approx(25_000_000, rel=1e-8)


def test_polygon_read_masks_and_rejects_nonoverlap(tmp_path):
    source = tmp_path/'source.h5'
    fixture(source, 'GSLC')
    area = gpd.GeoDataFrame(geometry=[box(500020, 8999925, 500080, 8999975)], crs=32722)
    run = process_area(source, tmp_path/'out', aoi=area, channels=['HH','HV'])
    report = json.loads((run/'manifest.json').read_text())
    assert report['scope'] == 'aoi' and report['covariance_complete']
    with rasterio.open(run/'HH.tif') as ds:
        assert ds.crs.to_epsg() == 32722
        assert np.isfinite(ds.read(1)).sum() == 30
    with pytest.raises(ValueError, match='overlap'):
        process_area(source, tmp_path/'out', aoi=square_aoi(10, 50), channels=['HH','HV'])


def test_table_preserves_selection_index():
    scenes = [{'umm': {'GranuleUR': 'scene-a'}}, {'umm': {'GranuleUR': 'scene-b'}}]
    assert scene_table(scenes).iloc[1]['scene'] == 'scene-b'
