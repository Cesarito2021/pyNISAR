"""Regenerate the six NISAR panels from the bundled measured subsets."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pynisar
from pynisar.display import _db

root = Path(__file__).resolve().parents[1]
target = root/'outputs/reproduced_panels'
target.mkdir(parents=True, exist_ok=True)
for mode in ['dual','quad']:
    window = pynisar.sample(mode)
    from rasterio.transform import array_bounds
    south_west_east_north = array_bounds(*window.intensity['HH'].shape, window.transform)
    west,south,east,north = south_west_east_north
    for channel in ['HH','HV']:
        fig, ax = plt.subplots(figsize=(5,4.6), layout='constrained')
        im = ax.imshow(_db(window.intensity[channel]), cmap='gray', vmin=-25, vmax=5,
                       extent=(west,east,south,north))
        ax.set_axis_off()
        fig.colorbar(im, ax=ax, orientation='horizontal', shrink=.85, label='Power (dB display)')
        fig.savefig(target/f'{mode}_{channel.lower()}.png', dpi=160)
        plt.close(fig)
    run = pynisar.process_sample(target, mode=mode)
    if mode == 'dual':
        pynisar.plot_halpha(run, output=target/'dual_halpha', dpi=160)
    else:
        pynisar.plot_haalpha(run, output=target/'quad_haalpha', dpi=160)
print(target)
