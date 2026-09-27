"""Figures and English case studies for map-geometry and radar-geometry products."""
from pathlib import Path
import json
import math
import numpy as np
import rasterio

from .display import _db,_limits

POWER = {'HH','HV','VH','VV','HV_reciprocal','span','product','sum_HH_HV',
         'pauli_odd','pauli_double','pauli_cross'}
LABELS = {'HV_reciprocal':'Reciprocal HV','HH_VV_ratio':'HH / VV','cpr':'Cross / co-pol',
          'ndsi':'NDSI','rvi':'RVI','prvi':'PRVI','dop':'DoP','entropy':'H','alpha':'α [degrees]',
          'anisotropy':'Anisotropy','pauli_odd':'Pauli odd power','pauli_double':'Pauli double power',
          'pauli_cross':'Pauli cross power','shannon':'Shannon H [nats]',
          'shannon_i':'Shannon HI [nats]','shannon_p':'Shannon HP [nats]',
          'reciprocity_residual':'HV/VH residual','ratio':'Co / cross-pol',
          'difference':'Co − cross-pol','fraction':'Cross-pol fraction','dprvi':'DpRVI'}


def _load(run):
    report=json.loads((run/'manifest.json').read_text())
    if report['status']!='complete':
        raise ValueError('A completed product analysis is required.')
    arrays={}
    for name,info in report['metrics'].items():
        with rasterio.open(run/info['file']) as ds:
            arrays[name]=ds.read(1,masked=True).filled(np.nan)
            bounds=ds.bounds
    return arrays,report,bounds


def _density(fig,ax,arrays,report):
    if 'entropy' not in arrays:
        ax.axis('off')
        ax.text(.02,.8,'Intensity-only product case',fontsize=22,fontweight='bold')
        ax.text(.02,.55,'Complex cross terms are absent.\nH–α, DoP and eigenvalue descriptors are not inferred.\n'
                'Arithmetic maps below use the stored intensity terms.',fontsize=13,linespacing=1.8)
        return
    from .halpha import draw_halpha
    mode = 'quad' if len(report['channels']) == 4 else 'dual'
    im, _ = draw_halpha(ax, arrays['entropy'], arrays['alpha'], mode=mode,
                       zones=mode == 'quad')
    fig.colorbar(im, ax=ax, label='# samples per bin', shrink=.8)
    ax.set_title('(a) H–α density · '+report['basis'])


def _map_panel(fig,ax,name,data,index,report,bounds,common):
    shown=_db(data) if name in POWER else data
    lo,hi=common if name in ('HH','HV','VV','VH','HV_reciprocal','span') else _limits(shown)
    color,cmap=('#996f2b','YlOrBr') if name in POWER else ('#3c665b','viridis')
    if name in ('entropy','alpha','anisotropy','dop'):color,cmap='#2d8195','YlGnBu'
    if name.startswith('shannon'):color,cmap='#71365b','magma'
    if name=='difference':lo,hi=-max(abs(lo),abs(hi)),max(abs(lo),abs(hi));cmap='RdBu_r'
    extent=[bounds.left,bounds.right,bounds.bottom,bounds.top]
    image=ax.imshow(shown,extent=extent,origin='upper',cmap=cmap,vmin=lo,vmax=hi,interpolation='nearest')
    label=LABELS.get(name,name.replace('_',' '))+(' [dB display]' if name in POWER else '')
    ax.set_title(f'({index+1}) {label}',loc='left',fontsize=10,fontweight='bold',color=color)
    ax.set_xticks([]);ax.set_yticks([])
    if index==0:
        from matplotlib import patheffects as pe
        halo=[pe.withStroke(linewidth=2,foreground='white')]
        unit='source columns' if report['geometry']=='radar' else 'm'
        width=bounds.right-bounds.left
        length=10**np.floor(np.log10(width/3))
        x=bounds.left+width*.06;y=bounds.bottom+(bounds.top-bounds.bottom)*.1
        ax.plot([x,x+length],[y,y],color='#10232a',lw=2,path_effects=halo)
        ax.text(x,y+(bounds.top-bounds.bottom)*.04,f'{length:g} {unit}',fontsize=8,path_effects=halo)
        if report['geometry']=='map':
            ax.annotate('Grid N',(.9,.92),xytext=(.9,.65),xycoords='axes fraction',ha='center',fontsize=8,
                        path_effects=halo,arrowprops={'arrowstyle':'->'})
    bar=fig.colorbar(image,ax=ax,orientation='horizontal',fraction=.07,pad=.04,aspect=24)
    bar.ax.tick_params(labelsize=8)


def plot_product(run, *, dpi=300, metrics=None):
    """Export product-specific H-alpha and metric panels; radar panels stay radar."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    run=Path(run);arrays,report,bounds=_load(run)
    default=['HH','HV','HV_reciprocal','VH','VV','span','HH_VV_ratio','ratio','difference','cpr','ndsi',
             'fraction','rvi','dprvi','prvi','entropy','alpha','anisotropy','dop','pauli_odd','pauli_double',
             'pauli_cross','shannon','shannon_i','shannon_p','reciprocity_residual']
    names=list(metrics) if metrics is not None else ([n for n in default if n in arrays] + [n for n in arrays if n not in default])
    if not names or not set(names)<=arrays.keys():raise ValueError('Select available metric names.')
    rows=math.ceil(len(names)/4)
    fig=Figure(figsize=(16,5+rows*2.6),layout='constrained');FigureCanvasAgg(fig)
    grid=fig.add_gridspec(rows+1,4,height_ratios=[2]+[1]*rows)
    _density(fig,fig.add_subplot(grid[0,:3]),arrays,report)
    note=fig.add_subplot(grid[0,3]);note.axis('off')
    shape=next(iter(arrays.values())).shape
    note.text(0,.95,'pyNISAR\n'+report['product']+' case study',fontsize=17,fontweight='bold',va='top',color='#173e48')
    note.text(0,.68,f"Channels: {' / '.join(report['channels'])}\n{shape[0]} × {shape[1]} output pixels\n"
              f"Looks: {report['looks']}\nGeometry: {report['geometry']}\nCRS: {report['crs'] or 'none (radar pixels)'}\n\n"
              'One bounded source window\n2–98% display stretches\nNo added Refined Lee filter\nNo land-cover labels inferred',
              fontsize=11,va='top',linespacing=1.7)
    power=[_db(arrays[n]).ravel() for n in names if n in ('HH','HV','VV','VH','HV_reciprocal','span')]
    common=_limits(np.concatenate(power)) if power else (0,1)
    for i,name in enumerate(names):
        _map_panel(fig,fig.add_subplot(grid[1+i//4,i%4]),name,arrays[name],i,report,bounds,common)
    fig.suptitle(f"NISAR {report['product']} | Polarimetric signatures and spatial patterns",fontsize=21,fontweight='bold')
    assumption='Reciprocity explicitly assumed. ' if report['reciprocity_assumption'] else ''
    fig.supxlabel(report['radiometry']+' · '+('Radar coordinates; not a geocoded map' if report['geometry']=='radar' else report['crs'])+
                  '\n'+assumption+'Source product calibration is not independently validated.',fontsize=10)
    for suffix in ('png','svg'):fig.savefig(run/f'case_study.{suffix}',dpi=dpi,bbox_inches='tight')
    return fig


def write_product_study(run):
    """Write an English report that distinguishes derived results from validation."""
    run=Path(run);_,r,_=_load(run)
    quad = len(r['channels']) == 4
    method = ('For quad-pol, the reciprocal cross channel is (HV+VH)/2 and C22=2|HV_reciprocal|². '
              'Pauli T3 supplies full-pol H (log base 3), alpha and anisotropy. Original four-channel '
              'covariance and a reciprocity residual are retained. The residual is mean |HV−VH|² / '
              '(mean |HV|² + mean |VH|²), not a calibration estimate.' if quad else
              'Dual-pol H uses log base 2 in the stated co/cross-pol C2 basis, where complex cross terms '
              'exist. The dual span is the two-channel power sum, not full-pol span. Intensity-only '
              'GCOV has no inferred H, alpha, DoP or Shannon covariance descriptors.')
    rows=['| Variable | Valid pixels | Mean | Median |','|---|---:|---:|---:|']
    for name,s in r['metrics'].items():
        mean=f"{s['mean']:.6g}" if s['mean'] is not None else 'undefined'
        median=f"{s['median']:.6g}" if s['median'] is not None else 'undefined'
        rows.append(f"| {name} | {s['count']} | {mean} | {median} |")
    text=f'''# pyNISAR — NISAR {r['product']} case study

## Objective and data
Demonstrate bounded, product-aware polarimetric processing with real NISAR data.
Source: `{r['source']}`.
Frequency: {r['frequency']}; measured channels: {r['channels']}.
Source window [row, column, height, width]: {r['window']}.
Requested longitude/latitude: {r['center_lonlat']}; radar pixel: {r['radar_pixel']}.
This run is a computational demonstration, not independent product calibration.

## Method
Geometry: **{r['geometry']}**; CRS: `{r['crs']}`; added block looks: `{r['looks']}`.
Radiometry: **{r['radiometry']}**, without any additional radiometric correction.
Covariance basis: **{r['basis']}**. Reciprocity assumption: `{r['reciprocity_assumption']}`.
GCOV uses the supplied covariance. GSLC/RSLC form covariance from complex samples.
{method}
Arithmetic dual-pol metrics need powers; phase/eigenvalue metrics require cross terms.
No Refined Lee or model-based Yamaguchi/MF3CF result is implied by native outputs.
Only complete finite sample blocks are retained; source quality-mask semantics and
noise correction have not been independently applied or validated.

## Results
The run exported {len(r['metrics'])} metric layers.
Measured response-body bytes read: **{r.get('response_body_bytes_read','local file / not measured')}**.
This byte count excludes HTTP/TLS overhead and NASA authentication metadata.
Skipped: {r['skipped'] or 'none among the selected native descriptors'}.

![Product case study figure](case_study.png)

**Figure.** H–alpha density where complex covariance is available, followed by
aligned descriptor panels. Density counts are pixel counts, not independent looks.
The layout is inspired by the supplied manuscript figure; values and scales are
calculated from this run. Full-pol density uses Pauli T3 and has no dual-pol envelope.
RSLC panels use radar row/column coordinates; they are not geocoded maps.

{chr(10).join(rows)}

## Limits and reproducibility
Do not compare different product windows as identical ground footprints without
explicit co-registration and matched support. Identical source pixel counts do not
imply equal ground area across GSLC, GCOV and RSLC. This is one acquisition/window,
not a geographic or temporal validation sample. Beta/provisional calibration and
mask limitations must be checked for the selected product release.
No biomass, land-cover or causal interpretation is established by these descriptors.
Positive repeated eigenvalues leave full-pol alpha non-unique; it is marked NaN.
Singular covariance has undefined finite Shannon differential entropy; it is NaN.
See [statistics.csv](statistics.csv), [manifest.json](manifest.json) and the covariance
archive for reproducibility. Equations and legacy differences are documented in
the package's product support guide. Pair processing is outside this case study.
'''
    path=run/'CASE_STUDY.md';path.write_text(text,encoding='utf-8');return path
