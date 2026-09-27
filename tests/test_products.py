import json
import h5py
import numpy as np
import pytest
import rasterio
from pynisar.products import inspect_product,read_window
from pynisar.analysis import analyze_product
from pynisar.quadpol import quadpol_metrics,reciprocal_c3


def fixture(path,product,quad=False,cross=True):
    rng=np.random.default_rng(5)
    channels=['HH','HV','VH','VV'] if quad else ['HH','HV']
    samples={p:rng.normal(size=(12,12))+1j*rng.normal(size=(12,12)) for p in channels}
    with h5py.File(path,'w') as h:
        kind='swaths' if product=='RSLC' else 'grids'
        g=h.create_group(f'/science/LSAR/{product}/{kind}/frequencyA')
        g['listOfPolarizations']=np.array(channels,dtype='S2')
        if product!='RSLC':
            g['xCoordinates']=500005.+np.arange(12)*10;g['yCoordinates']=9000000.-np.arange(12)*10
            g['xCoordinateSpacing']=10.;g['yCoordinateSpacing']=-10.;g['projection']=32722
        for i,p in enumerate(channels):
            if product!='GCOV':
                g[p]=samples[p].astype('complex64')
            else:
                for q in channels[i:]:
                    if p!=q and not cross:continue
                    a=samples[p]*samples[q].conj()
                    g[p+q]=a.real.astype('float32') if p==q else a.astype('complex64')


def test_gcov_without_phase_never_fabricates_entropy(tmp_path):
    file=tmp_path/'unrelated_filename.h5';fixture(file,'GCOV',cross=False)
    assert inspect_product(file)['off_diagonal_available'] is False
    run=analyze_product(file,tmp_path,window_size=6,looks=(2,2))
    report=json.loads((run/'manifest.json').read_text())
    assert len(report['metrics'])==10 and 'entropy' not in report['metrics']
    assert report['skipped'] and 'nominal gamma0' in report['radiometry']


def test_radar_geometry_and_frequency_guards(tmp_path):
    file=tmp_path/'rslc.h5';fixture(file,'RSLC')
    with pytest.raises(ValueError,match='radar geometry'):
        read_window(file,center=(-50,-9))
    with pytest.raises(ValueError,match='absent'):
        read_window(file,frequency='B')
    run=analyze_product(file,tmp_path,pixel=(6,6),window_size=6,looks=(2,2))
    with rasterio.open(run/'HH.tif') as ds:
        assert ds.crs is None and ds.tags()['geometry']=='radar'
        assert ds.transform.a==2 and ds.transform.e==2


def test_quad_reciprocity_and_crosspol_scaling():
    # Equal reciprocal cross-pol channels -> C22=2*HV, not HV.
    vector=np.array([1,2,2,3],complex)
    c4=np.outer(vector,vector.conj())[None,None]
    c3=reciprocal_c3(c4,['HH','HV','VH','VV'])
    np.testing.assert_allclose(c3[0,0,1,1],8)
    metrics=quadpol_metrics(c3)
    np.testing.assert_allclose(metrics['HV_reciprocal'],4)
    np.testing.assert_allclose(metrics['span'],18)
    np.testing.assert_allclose(metrics['rvi'],32/18)
    trihedral=np.outer([1,0,1],[1,0,1])[None,None]
    dihedral=np.outer([1,0,-1],[1,0,-1])[None,None]
    np.testing.assert_allclose(quadpol_metrics(trihedral)['alpha'],0,atol=1e-6)
    np.testing.assert_allclose(quadpol_metrics(dihedral)['alpha'],90)
    iso=quadpol_metrics(np.eye(3)[None,None])
    np.testing.assert_allclose(iso['entropy'],1)
    np.testing.assert_allclose(iso['dop'],0,atol=1e-7)
    assert np.isnan(iso['alpha']).all()


@pytest.mark.parametrize('product',['GSLC','GCOV','RSLC'])
def test_quad_all_products_export_normalized_c3(tmp_path,product):
    file=tmp_path/'scene.h5';fixture(file,product,quad=True)
    with pytest.raises(ValueError,match='reciprocal=True'):
        analyze_product(file,tmp_path,window_size=12,looks=(2,2))
    run=analyze_product(file,tmp_path,window_size=12,looks=(2,2),reciprocal=True)
    report=json.loads((run/'manifest.json').read_text())
    assert report['status']=='complete' and report['basis']=='reciprocal C3 / Pauli T3'
    assert len(report['metrics']) == 18
    assert {'HH', 'HV', 'VH', 'VV'} <= report['metrics'].keys()
    assert not any(name.startswith('measured_') for name in report['metrics'])
    with rasterio.open(run/'C3/C22.tif') as ds: c22=ds.read(1)
    with rasterio.open(run/'HV_reciprocal.tif') as ds:hv=ds.read(1)
    np.testing.assert_allclose(c22,2*hv)
