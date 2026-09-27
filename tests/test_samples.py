import json
import numpy as np
import pytest
import rasterio
import pynisar
from pynisar.maps import raster_overlay


@pytest.mark.parametrize('mode',['dual','quad'])
def test_measured_sample_reproduces_saved_statistics(tmp_path, mode):
    from importlib.resources import files
    expected=json.loads(files('pynisar').joinpath('data',mode,'manifest.json').read_text())
    run=pynisar.process_sample(tmp_path,mode=mode)
    actual=json.loads((run/'manifest.json').read_text())
    assert actual['status']=='complete'
    assert actual['channels']==expected['channels']
    assert actual['window']==expected['window'] and actual['looks']==expected['looks']
    assert set(actual['metrics'])==set(expected['metrics'])
    for name in actual['metrics']:
        np.testing.assert_allclose(actual['metrics'][name]['mean'],expected['metrics'][name]['mean'],rtol=1e-5,atol=1e-8)
    rgba,bounds,scale=raster_overlay(run/'HH.tif',metric='HH')
    assert rgba.shape[2]==4 and bounds[0][0]<bounds[1][0] and bounds[0][1]<bounds[1][1]
    assert -91<bounds[0][1]<-89 and 46<bounds[0][0]<47
    assert scale[0]<scale[1]


def test_radar_raster_not_mapped(tmp_path):
    from affine import Affine
    path=tmp_path/'radar.tif'
    with rasterio.open(path,'w',driver='GTiff',height=2,width=2,count=1,dtype='float32',transform=Affine(2,0,1,0,2,1)) as ds:
        ds.write(np.ones((2,2),dtype='float32'),1)
    with pytest.raises(ValueError,match='Radar coordinates'):
        raster_overlay(path,metric='HH')
