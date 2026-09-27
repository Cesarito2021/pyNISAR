import json
import geopandas as gpd
import numpy as np
import pytest
import rasterio
from shapely.geometry import box, Polygon
from test_products import fixture
from pynisar import process, process_tile, process_batch


@pytest.mark.parametrize('product',['GSLC','GCOV','RSLC'])
def test_chunks_equal_single_window_and_cleanup(tmp_path,product):
    source=tmp_path/'scene.h5'; fixture(source,product,quad=True)
    reference=process(source,tmp_path/'reference',window_size=12,looks=(2,2),reciprocal=True)
    run=process_tile(source,tmp_path/'chunked',scope='tile',chunk_size=5,
                     looks=(2,2),reciprocal=True,delete_source=True)
    assert not source.exists()
    report=json.loads((run/'manifest.json').read_text())
    assert report['source_deleted'] and report['chunks_written']==9
    assert len(report['metrics'])==18
    assert not (run/'covariance.npz').exists()
    for name in report['metrics']:
        with rasterio.open(reference/(name+'.tif')) as ref,rasterio.open(run/(name+'.tif')) as dst:
            assert dst.transform==ref.transform and dst.crs==ref.crs
            np.testing.assert_allclose(dst.read(1),ref.read(1),rtol=1e-5,atol=1e-5,equal_nan=True)


def test_aoi_hole_crop_and_chunk_edges(tmp_path):
    source=tmp_path/'scene.h5'; fixture(source,'GSLC')
    # Grid edges: x=500000..500120, y=8999885..9000005.
    polygon=Polygon(box(500020,8999905,500100,8999985).exterior.coords,
                    [box(500040,8999925,500080,8999965).exterior.coords])
    aoi=gpd.GeoDataFrame(geometry=[polygon],crs=32722)
    run=process_tile(source,tmp_path/'out',aoi=aoi,chunk_size=3,metrics=['HH'])
    with rasterio.open(run/'HH.tif') as ds:
        a=ds.read(1)
        # Round-trip projection may add an all-nodata edge. Pixel-center mask is exact.
        assert np.isfinite(a).sum()==48
        assert ds.crs.to_epsg()==32722
        assert np.isnan(a).any()
    assert source.exists()


def test_failure_keeps_source_and_batch_continues(tmp_path,monkeypatch):
    source=tmp_path/'scene.h5'; fixture(source,'GSLC')
    import pynisar.batch as batch
    original=batch.read_window
    calls=[]
    def failing(*args,**kwargs):
        calls.append(1)
        if len(calls)>2: raise OSError('simulated read failure')
        return original(*args,**kwargs)
    monkeypatch.setattr(batch,'read_window',failing)
    with pytest.raises(OSError,match='simulated'):
        process_tile(source,tmp_path/'out',scope='tile',chunk_size=4,delete_source=True)
    assert source.exists()
    manifest=next((tmp_path/'out').glob('*/manifest.json'))
    assert json.loads(manifest.read_text())['status']=='failed'
    monkeypatch.setattr(batch,'read_window',original)
    results=process_batch([tmp_path/'missing.h5',source],tmp_path/'batch',
                          scope='tile',chunk_size=4,workers=2)
    assert [r['status'] for r in results]==['failed','complete']
    assert source.exists()
    with pytest.raises(ValueError,match='Duplicate'):
        process_batch([source,source],tmp_path/'batch',delete_source=True)


def test_radar_aoi_rejected_without_deletion(tmp_path):
    source=tmp_path/'scene.h5'; fixture(source,'RSLC')
    with pytest.raises(ValueError,match='radar geometry'):
        process_tile(source,tmp_path,scope='aoi',aoi='unused.geojson',delete_source=True)
    assert source.exists()


def test_reads_bounded_trailing_pixels_and_cleanup_error(tmp_path,monkeypatch):
    source=tmp_path/'scene.h5'; fixture(source,'GSLC')
    import pynisar.batch as batch
    original=batch.read_window
    windows=[]
    def tracked(*args,**kwargs):
        windows.append(kwargs['raster_window'])
        return original(*args,**kwargs)
    monkeypatch.setattr(batch,'read_window',tracked)
    from pathlib import Path
    unlink=Path.unlink
    def denied(path,*args,**kwargs):
        if path==source: raise PermissionError('simulated cleanup failure')
        return unlink(path,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',denied)
    run=process_tile(source,tmp_path/'out',scope='tile',looks=(5,5),chunk_size=7,
                     metrics=['HH'],delete_source=True)
    assert source.exists()
    report=json.loads((run/'manifest.json').read_text())
    assert report['status']=='complete' and not report['source_deleted']
    assert 'simulated cleanup' in report['cleanup_error']
    assert report['trailing_pixels_dropped']==[2,2]
    assert all(w[2]<=7 and w[3]<=7 for w in windows)
    with rasterio.open(run/'HH.tif') as ds:
        assert ds.shape==(2,2)


def test_bbox_clip_and_invalid_window(tmp_path):
    source=tmp_path/'scene.h5'; fixture(source,'GSLC')
    from pynisar import read
    from rasterio.warp import transform_bounds
    bounds=transform_bounds(32722,4326,500020,8999905,500100,8999985)
    run=process_tile(source,tmp_path/'out',bbox=bounds,metrics=['HH'],chunk_size=4)
    with rasterio.open(run/'HH.tif') as ds:
        assert 0<np.isfinite(ds.read(1)).sum()<144
    with pytest.raises(ValueError,match='divisible'):
        read(source,raster_window=(0,0,5,5),looks=(2,2))

