"""Bounded-memory tile processing with explicit, success-only source cleanup."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
import csv
import json
import math
import uuid

import numpy as np
import rasterio
from affine import Affine
from rasterio.features import geometry_mask
from rasterio.windows import Window

from .analysis import _derive
from .products import inspect_product, read_window


def _write_manifest(run, report):
    temporary = run/'manifest.tmp'
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(run/'manifest.json')


def process_tile(source, output, *, scope='aoi', aoi=None, bbox=None, layer=None,
                 frequency='A', channels=None, looks=(1, 1), chunk_size=256,
                 reciprocal=False, metrics=None, delete_source=False):
    """Write one set of metric GeoTIFFs, reading at most one chunk at a time.

    scope='aoi' requires a polygon AOI; scope='tile' covers the native tile.
    AOI masks use output pixel centers, after boxcar averaging. Looks align to
    the source origin; incomplete trailing look cells are dropped explicitly.
    RSLC supports tile scope only, without a geographic CRS. No full covariance
    archive or figure is generated. delete_source=True permanently removes only
    the supplied local HDF5 after all outputs close and validate successfully.
    """
    source = Path(source).resolve(strict=True)
    if not source.is_file() or source.suffix.lower() not in ('.h5', '.hdf5', '.hdf'):
        raise ValueError('Use a local HDF5 file.')
    if scope not in ('aoi', 'tile'):
        raise ValueError('scope must be aoi or tile.')
    if scope == 'aoi' and (aoi is None) == (bbox is None):
        raise ValueError('AOI scope requires exactly one polygon AOI or bbox.')
    if bbox is not None:
        if len(bbox) != 4 or not all(math.isfinite(v) for v in bbox):
            raise ValueError('bbox requires four finite WGS84 coordinates.')
        west,south,east,north = bbox
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError('bbox must be ordered WGS84 west, south, east, north.')
        if layer is not None:
            raise ValueError('layer applies only to a GeoPackage AOI.')
    if type(delete_source) is not bool:
        raise ValueError('delete_source must be True or False.')
    if type(chunk_size) is not int or not 1 <= chunk_size <= 4096:
        raise ValueError('chunk_size must be an integer from 1 to 4096.')
    if len(looks) != 2 or any(type(v) is not int or not 1 <= v <= chunk_size for v in looks):
        raise ValueError('looks must be positive integers no larger than chunk_size.')
    ly,lx = looks
    source_stat = source.stat()
    info = inspect_product(source, frequency=frequency)
    shape = next(iter(info['datasets'].values()))['shape']
    height,width = shape[0]//ly,shape[1]//lx
    if min(height,width) == 0:
        raise ValueError('Tile is smaller than the selected looks.')
    # Validate the grid, channel selection and scientific interpretation first.
    probe = read_window(source, frequency=frequency, channels=channels, looks=looks,
                        raster_window=(0,0,ly,lx))
    available,_,basis,skipped = _derive(probe, reciprocal)
    names = list(available) if metrics is None else list(metrics)
    if not names or len(set(names)) != len(names) or not set(names) <= set(available):
        raise ValueError('metrics must be distinct names available for these channels/covariance terms.')
    affine = probe.transform or Affine(lx,0,0,0,ly,0)
    crs = probe.crs
    geometries = None
    r0,c0,r1,c1 = 0,0,height,width
    if scope == 'aoi':
        if crs is None:
            raise ValueError('Geographic AOI clipping requires GSLC or GCOV; RSLC is in radar geometry.')
        from .aoi import read_aoi
        from shapely.ops import transform
        if bbox is not None:
            import geopandas as gpd
            from shapely.geometry import box
            aoi = gpd.GeoDataFrame(geometry=[box(*bbox)],crs=4326)
        frame = read_aoi(aoi, layer=layer).to_crs(crs)
        geometries = list(frame.geometry)
        inverse = ~affine
        bounds = transform(lambda x,y,z=None: inverse*(x,y), frame.geometry.union_all()).bounds
        c0,r0 = max(0,math.floor(bounds[0])),max(0,math.floor(bounds[1]))
        c1,r1 = min(width,math.ceil(bounds[2])),min(height,math.ceil(bounds[3]))
        if c0 >= c1 or r0 >= r1:
            raise ValueError('AOI does not overlap this tile.')
    output_affine = affine*Affine.translation(c0,r0)
    run = Path(output).resolve()/('tile-'+source.stem+'-'+uuid.uuid4().hex)
    run.mkdir(parents=True)
    report = dict(probe.info, status='running', scope=scope, source=str(source),
                  source_deleted=False, delete_source_requested=delete_source,
                  basis=basis, skipped=skipped, reciprocity_assumption=reciprocal,
                  window=[r0*ly,c0*lx,(r1-r0)*ly,(c1-c0)*lx],
                  chunk_size=chunk_size, chunks_written=0,
                  trailing_pixels_dropped=[shape[0]%ly,shape[1]%lx],
                  mask_rule='output pixel center after boxcar averaging' if geometries else None,
                  metrics={}, covariance_saved=False)
    if geometries:
        report['aoi'] = {'crs':str(crs), 'geometries':[g.__geo_interface__ for g in geometries]}
    _write_manifest(run, report)
    stats = {name:dict(count=0,mean=0.,m2=0.,min=None,max=None) for name in names}
    try:
        with ExitStack() as stack:
            writers = {}
            for name in names:
                dst = stack.enter_context(rasterio.open(run/(name+'.tif'),'w',driver='GTiff',
                    height=r1-r0,width=c1-c0,count=1,dtype='float32',crs=crs,
                    transform=output_affine,nodata=np.nan,compress='deflate',tiled=True,BIGTIFF='YES'))
                dst.set_band_description(1,name)
                dst.update_tags(geometry=info['geometry'],radiometry=probe.info['radiometry'],quantity=name)
                writers[name] = dst
            included = 0
            for r in range(r0,r1,chunk_size//ly):
                for c in range(c0,c1,chunk_size//lx):
                    nr,nc = min(chunk_size//ly,r1-r),min(chunk_size//lx,c1-c)
                    mask = (geometry_mask(geometries,out_shape=(nr,nc),
                            transform=affine*Affine.translation(c,r),invert=True)
                            if geometries else np.ones((nr,nc),dtype=bool))
                    included += int(mask.sum())
                    if mask.any():
                        block = read_window(source,frequency=frequency,channels=channels,looks=looks,
                                            raster_window=(r*ly,c*lx,nr*ly,nc*lx))
                        values,_,_,_ = _derive(block,reciprocal)
                    for name,dst in writers.items():
                        a = np.where(mask,values[name],np.nan).astype('float32') if mask.any() else np.full((nr,nc),np.nan,dtype='float32')
                        dst.write(a,1,window=Window(c-c0,r-r0,nc,nr))
                        v = a[np.isfinite(a)].astype('float64')
                        if v.size:
                            s = stats[name]
                            n = int(v.size); mean = float(v.mean()); delta = mean-s['mean']; total = s['count']+n
                            s['m2'] += float(np.sum((v-mean)**2))+delta**2*s['count']*n/total
                            s['mean'] += delta*n/total
                            s['count'] = total
                            s['min'] = float(v.min()) if s['min'] is None else min(s['min'],float(v.min()))
                            s['max'] = float(v.max()) if s['max'] is None else max(s['max'],float(v.max()))
                    report['chunks_written'] += 1
            if included == 0:
                raise ValueError('AOI contains no output pixel centers at these looks.')
        for name,s in stats.items():
            with rasterio.open(run/(name+'.tif')) as ds:
                if ds.shape != (r1-r0,c1-c0) or ds.transform != output_affine:
                    raise RuntimeError('Output grid verification failed.')
            report['metrics'][name] = dict(file=name+'.tif',shape=[r1-r0,c1-c0],
                count=s['count'],finite_fraction=s['count']/((r1-r0)*(c1-c0)),
                mean=s['mean'] if s['count'] else None,min=s['min'],max=s['max'],
                std=math.sqrt(max(0,s['m2']/s['count'])) if s['count'] else None)
        if not any(s['count'] for s in stats.values()):
            raise ValueError('Selected products contain no finite output pixels; source retained.')
        with (run/'statistics.csv').open('w',newline='',encoding='utf-8') as f:
            writer = csv.DictWriter(f,fieldnames=['metric','count','finite_fraction','min','mean','max','std'])
            writer.writeheader()
            for name,s in report['metrics'].items():
                writer.writerow({'metric':name,**{k:s[k] for k in writer.fieldnames[1:]}})
        report['status'] = 'complete'
        _write_manifest(run,report)
    except Exception as exc:
        report.update(status='failed',error=str(exc))
        _write_manifest(run,report)
        raise
    if delete_source:
        try:
            current = source.stat()
            if (current.st_size,current.st_mtime_ns,current.st_ino) != (source_stat.st_size,source_stat.st_mtime_ns,source_stat.st_ino):
                raise OSError('Source changed during processing; retained instead of deleting.')
            source.unlink()
            report['source_deleted'] = True
        except OSError as exc:
            report['cleanup_error'] = str(exc)
        _write_manifest(run,report)
    return run


def process_batch(sources, output, *, workers=1, **options):
    """Process local tiles sequentially or with 2–4 concurrent tile workers.

    Memory and I/O scale with workers. Duplicate paths are rejected. A failed
    tile retains its source and records its error; other tiles finish normally.
    Inspect every returned status. This does not download the input inventory.
    """
    if type(workers) is not int or not 1 <= workers <= 4:
        raise ValueError('workers must be an integer from 1 to 4.')
    paths = [Path(p).resolve() for p in sources]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate source paths are not allowed in a batch.')
    def task(source):
        try:
            run = process_tile(source,output,**options)
            report = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
            return dict(source=str(source),run=str(run),status='complete',
                        source_deleted=report['source_deleted'],cleanup_error=report.get('cleanup_error'))
        except Exception as exc:
            return dict(source=str(source),status='failed',error=str(exc))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(task,paths))
