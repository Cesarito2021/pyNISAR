"""Regenerate the README panels from measured bundled observations."""
from pathlib import Path
import shutil
import pynisar
root = Path(__file__).resolve().parents[1]
output = root/'outputs/reproduced_panels'
output.mkdir(parents=True,exist_ok=True)
for mode in ('dual','quad'):
    run = pynisar.process_sample(output,mode=mode)
    images = pynisar.plot_gallery(run)
    for source,name in zip(images,('hh','hv','halpha' if mode=='dual' else 'haalpha')):
        shutil.copyfile(source,output/f'{mode}_{name}.png')
print(output)
