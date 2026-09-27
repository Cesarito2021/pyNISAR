"""Joint H-alpha sample density, with explicit dual/quad conventions."""
from pathlib import Path
import json
import numpy as np


def draw_halpha(ax, entropy, alpha, *, mode, bins=120, zones=False):
    """Draw logarithmic sample counts (not KDE or a land-cover classification).

    Dual H uses log2; quad H uses log3 and Pauli alpha. Quad boundary curves
    are conventional Cloude-Pottier reference curves, not a data validity mask.
    All finite in-range pairs are retained, including H=0, alpha=0.
    """
    from matplotlib.colors import LogNorm
    if mode not in ('dual', 'quad'):
        raise ValueError('mode must be dual or quad.')
    if zones and mode != 'quad':
        raise ValueError('Full-pol reference zones cannot be assigned to dual-pol.')
    h, a = np.asarray(entropy, float), np.asarray(alpha, float)
    if h.shape != a.shape or h.size == 0:
        raise ValueError('H and alpha must have the same nonempty shape.')
    valid = np.isfinite(h) & np.isfinite(a) & (h >= 0) & (h <= 1) & (a >= 0) & (a <= 90)
    if not valid.any():
        raise ValueError('No finite in-range H-alpha pairs.')
    if not isinstance(bins, int) or isinstance(bins, bool) or bins < 2:
        raise ValueError('bins must be an integer >= 2.')
    def entropy_of(p):
        return -(p*np.log(np.maximum(p, 1e-300))).sum(-1)/np.log(p.shape[-1])
    if mode == 'dual':
        p = np.linspace(1, .5, 1500)
        x = entropy_of(np.stack([p, 1-p], -1))
        lower, upper = 90*(1-p), 90*p
        ax.fill_between(x, 0, lower, color='#d4d4d4', zorder=0)
        ax.fill_between(x, upper, 90, color='#d4d4d4', zorder=0)
        ax.plot(x, lower, color='#555555', lw=.8)
        ax.plot(x, upper, color='#555555', lw=.8)
    else:
        p = np.linspace(1, 1/3, 1500)
        x = entropy_of(np.stack([p, (1-p)/2, (1-p)/2], -1))
        lower = 90*(1-p)
        ax.fill_between(x, 0, lower, color='#d4d4d4', zorder=0)
        ax.plot(x, lower, color='#555555', lw=.8)
        q = np.linspace(0, 1/3, 1500)
        xu = entropy_of(np.stack([(1-q)/2, (1-q)/2, q], -1))
        upper = 90*(1-q)
        ax.fill_between(xu, upper, 90, color='#d4d4d4', zorder=0)
        ax.plot(xu, upper, color='#555555', lw=.8)
    counts, xe, ye = np.histogram2d(h[valid], a[valid], bins=bins, range=((0, 1), (0, 90)))
    mesh = ax.pcolormesh(xe, ye, np.ma.masked_less(counts.T, 1), cmap='jet',
                         norm=LogNorm(vmin=1, vmax=max(2, counts.max())),
                         shading='flat', rasterized=True)
    if zones:
        for v in (.5, .9):
            ax.axvline(v, color='#252525', ls='--', lw=.7)
        for y, left, right in [(42.5, 0, .5), (47.5, 0, .5), (40, .5, 1), (50, .5, .9), (60, .9, 1)]:
            ax.hlines(y, left, right, color='#252525', ls='--', lw=.7)
    ax.set(xlim=(0, 1), ylim=(0, 90), xlabel='Entropy, H', ylabel='Alpha (°)',
           title=f'{mode.capitalize()}-pol H–α density')
    ax.text(.03, .97, f'n = {valid.sum():,}\nMean H = {h[valid].mean():.3f}\nMean α = {a[valid].mean():.2f}°',
            va='top', transform=ax.transAxes, fontsize=9,
            bbox=dict(facecolor='white', alpha=.85, edgecolor='none'))
    return mesh, dict(mode=mode, bins=bins, valid_pairs=int(valid.sum()),
                      excluded_pairs=int(valid.size-valid.sum()), reference_zones=zones,
                      normalization='logarithmic count per 2D bin')


def plot_halpha(entropy, alpha, output, *, mode, zones=False, bins=120, dpi=300):
    """Export joint density as PNG/SVG and a count/convention JSON sidecar."""
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    fig = Figure(figsize=(7.8, 6.3), layout='constrained')
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    mesh, report = draw_halpha(ax, entropy, alpha, mode=mode, bins=bins, zones=zones)
    fig.colorbar(mesh, ax=ax, label='# samples per bin')
    note = ('C2 basis · log₂ entropy · no full-pol classification zones' if mode == 'dual'
            else 'Pauli T3 · log₃ entropy · reference curves; no land-cover classes inferred')
    fig.supxlabel(note, fontsize=9)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(out.with_suffix('.'+ext), dpi=dpi)
    out.with_suffix('.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return fig


def plot_htheta(entropy, theta_fp, output, *, bins=100, dpi=300):
    """Quad MF3CF polar density: radius 1-H, angle 2*theta_FP in degrees.

    Theta_FP is the MF3CF parameter in [-45,45], not eigenvector alpha.
    Reference classification zones are intentionally not inferred from counts.
    Use H and theta from the same grid and covariance/filter support.
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.colors import LogNorm
    h, theta = np.asarray(entropy, float), np.asarray(theta_fp, float)
    if h.shape != theta.shape:
        raise ValueError('H and theta_FP must share a shape.')
    if not isinstance(bins, int) or isinstance(bins, bool) or bins < 2:
        raise ValueError('bins must be an integer >= 2.')
    valid = np.isfinite(h) & np.isfinite(theta) & (h >= 0) & (h <= 1) & (np.abs(theta) <= 45)
    if not valid.any():
        raise ValueError('No finite H and MF3CF theta_FP pairs in range.')
    counts, angles, radii = np.histogram2d(np.deg2rad(2*theta[valid]), 1-h[valid],
        bins=bins, range=((-np.pi/2, np.pi/2), (0, 1)))
    fig = Figure(figsize=(8, 5.5), layout='constrained'); FigureCanvasAgg(fig)
    ax = fig.add_subplot(projection='polar')
    ax.set_theta_zero_location('N'); ax.set_theta_direction(-1)
    ax.set_thetamin(-90); ax.set_thetamax(90); ax.set_ylim(0, 1)
    ax.grid(False)
    im = ax.pcolormesh(angles, radii, np.ma.masked_less(counts.T, 1), cmap='jet',
        norm=LogNorm(1, max(2, counts.max())), shading='flat', rasterized=True)
    ax.set_xticks(np.deg2rad([-90, -45, 0, 45, 90]))
    ax.set_xticklabels(['−90°', '−45°', '0°', '45°', '90°'])
    ax.set_yticks([.3, .5, 1]); ax.set_yticklabels(['0.3', '0.5', '1.0'])
    ax.grid(True, linestyle=':', alpha=.5)
    ax.set_title('Quad-pol H–θFP density', pad=20)
    fig.colorbar(im, ax=ax, shrink=.65, label='# samples per polar bin', pad=.12)
    fig.supxlabel(f'Radius = 1−H · angle = 2θFP · {valid.sum():,} common valid pixels', fontsize=11)
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(out.with_suffix('.'+ext), dpi=dpi)
    out.with_suffix('.json').write_text(json.dumps(dict(mode='quad', bins=bins,
        valid_pairs=int(valid.sum()), excluded_pairs=int(valid.size-valid.sum()),
        radius='1-H', angle='2*theta_FP [degrees]', source_theta='MF3CF',
        normalization='logarithmic count per polar bin'), indent=2), encoding='utf-8')
    return fig


def plot_haalpha(entropy, anisotropy, alpha, output, *, bins=70, dpi=300):
    """Quad-pol H-A-alpha cube with three 2D marginal count projections.

    These faces are not a joint 3D histogram. All use the same finite-pixel set,
    bin count and logarithmic color normalization. No sampling or smoothing.
    """
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.colors import LogNorm
    from matplotlib.cm import ScalarMappable
    from matplotlib import colormaps
    h, a, alpha = [np.asarray(v, float) for v in (entropy, anisotropy, alpha)]
    if h.shape != a.shape or h.shape != alpha.shape:
        raise ValueError('H, A and alpha must share a shape.')
    if not isinstance(bins, int) or isinstance(bins, bool) or bins < 2:
        raise ValueError('bins must be an integer >= 2.')
    valid = (np.isfinite(h) & np.isfinite(a) & np.isfinite(alpha) &
             (h >= 0) & (h <= 1) & (a >= 0) & (a <= 1) & (alpha >= 0) & (alpha <= 90))
    if not valid.any():
        raise ValueError('No finite in-range H-A-alpha triples.')
    h, a, alpha = h[valid], a[valid], alpha[valid]
    projections = [np.histogram2d(x, y, bins=bins, range=r) for x, y, r in
                   [(h, a, ((0, 1), (0, 1))), (h, alpha, ((0, 1), (0, 90))),
                    (a, alpha, ((0, 1), (0, 90)))]]
    norm = LogNorm(1, max(2, max(p[0].max() for p in projections)))
    fig = Figure(figsize=(9, 7.5), layout='constrained'); FigureCanvasAgg(fig)
    ax = fig.add_subplot(projection='3d')
    for face, (counts, xe, ye) in enumerate(projections):
        x, y = np.meshgrid(xe, ye, indexing='ij')
        colors = colormaps['jet'](norm(np.maximum(counts, 1)))
        colors[..., 3] = counts > 0
        coords = ((x, y, np.full(x.shape, 90)) if face == 0 else
                  (x, np.zeros(x.shape), y) if face == 1 else
                  (np.zeros(x.shape), x, y))
        ax.plot_surface(*coords, facecolors=colors, rstride=1, cstride=1,
                        linewidth=0, antialiased=False, shade=False, rasterized=True)
    ax.set(xlim=(0, 1), ylim=(0, 1), zlim=(0, 90), xlabel='Entropy, H',
           ylabel='Anisotropy, A', zlabel='Alpha (°)')
    ax.view_init(elev=23, azim=-135)
    ax.set_xticks([.2, .4, .6, .8, 1])
    ax.set_box_aspect((1, 1, 1))
    fig.colorbar(ScalarMappable(norm=norm, cmap='jet'), ax=ax, shrink=.7,
                 pad=.1, label='# samples per projected bin')
    fig.suptitle('Quad-pol H–A–α | Three density projections', fontsize=17)
    fig.supxlabel(f'{len(h):,} common valid pixels · Pauli T3 · shared logarithmic count scale', fontsize=10)
    out = Path(output); out.parent.mkdir(parents=True, exist_ok=True)
    for ext in ('png', 'svg'):
        fig.savefig(out.with_suffix('.'+ext), dpi=dpi)
    out.with_suffix('.json').write_text(json.dumps(dict(mode='quad', bins=bins,
        valid_triples=len(h), excluded_triples=int(valid.size-valid.sum()),
        representation='three 2D marginal count projections; not joint 3D density'), indent=2), encoding='utf-8')
    return fig
