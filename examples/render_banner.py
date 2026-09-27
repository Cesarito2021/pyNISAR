"""Render the README's SVG banner from measured VH power and the Python logo."""
from pathlib import Path
import base64
import io
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import rasterio

root = Path(__file__).resolve().parents[1]
with rasterio.open(root/'src/pynisar/data/quad/VH.tif') as ds:
    power = ds.read(1, masked=True).astype(float).filled(np.nan)
db = 10*np.log10(power, out=np.full_like(power,np.nan), where=power>0)
low,high = np.nanpercentile(db,[2,98])
buffer=io.BytesIO()
plt.imsave(buffer, db, format='png', cmap='gray', vmin=low, vmax=high)
raster = base64.b64encode(buffer.getvalue()).decode('ascii')
logo = base64.b64encode((root/'docs/python-logo-only.svg').read_bytes()).decode('ascii')
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="400" viewBox="0 0 1200 400" role="img" aria-labelledby="title description">
<title id="title">pyNISAR</title>
<desc id="description">NISAR processing in Python. White title on a black header with a measured grayscale VH radar background and a small Python logo at top right.</desc>
<defs><linearGradient id="shade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="black" stop-opacity="1"/><stop offset="0.38" stop-color="black" stop-opacity=".93"/><stop offset="1" stop-color="black" stop-opacity=".23"/></linearGradient></defs>
<rect width="1200" height="400" fill="black"/>
<image x="0" y="0" width="1200" height="400" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/png;base64,{raster}"/>
<rect width="1200" height="400" fill="url(#shade)"/>
<g font-family="Arial, Helvetica, sans-serif" fill="white"><text x="48" y="111" font-size="86" font-weight="700">pyNISAR</text><text x="51" y="157" font-size="25" fill="#e3e3e3">Discover, process and visualize NISAR L-band SAR</text></g>
<image x="1080" y="30" width="74" height="90" preserveAspectRatio="xMidYMid meet" xlink:href="data:image/svg+xml;base64,{logo}"/>
</svg>'''
(root/'docs/banner.svg').write_text(svg,encoding='utf-8')
print('Rendered docs/banner.svg from measured GCOV VH, with a 2–98% dB stretch.')
