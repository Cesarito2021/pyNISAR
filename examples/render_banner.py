"""Render measured HV at reduced magnification, without smoothing or cropping."""
from pathlib import Path
import base64, io
import numpy as np
import rasterio
from PIL import Image
root=Path(__file__).resolve().parents[1]
with rasterio.open(root/'src/pynisar/data/quad/HV.tif') as ds:
    a=ds.read(1,masked=True).astype(float).filled(np.nan)
db=10*np.log10(a,out=np.full_like(a,np.nan),where=a>0)
lo,hi=np.nanpercentile(db,[2,98])
gray=np.nan_to_num(np.clip((db-lo)/(hi-lo),0,1),nan=0)
im=Image.fromarray((gray*255).astype('uint8')).resize((384,384),Image.Resampling.NEAREST)
b=io.BytesIO(); im.save(b,format='PNG')
raster=base64.b64encode(b.getvalue()).decode()
logo=base64.b64encode((root/'docs/python-logo-only.svg').read_bytes()).decode()
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1200" height="400" viewBox="0 0 1200 400" role="img" aria-labelledby="title desc">
<title id="title">pyNISAR</title><desc id="desc">Full measured HV subset at three-times native pixel size with nearest-neighbor display, no smoothing or crop. Black background, white pyNISAR title, Python logo at top right.</desc>
<rect width="1200" height="400" fill="#050708"/>
<image x="708" y="8" width="384" height="384" style="image-rendering:pixelated" xlink:href="data:image/png;base64,{raster}"/>
<g font-family="Arial, Helvetica, sans-serif" fill="white"><text x="48" y="122" font-size="86" font-weight="700">pyNISAR</text><text x="52" y="176" font-size="23">NASA–ISRO L-band SAR in Python</text><text x="52" y="212" font-size="19" fill="#b8c7cc">Discover · screen · download · process</text><text x="52" y="352" font-size="15" fill="#9dacb2">Polarimetric products · reproducible research</text></g>
<rect x="724" y="337" width="181" height="42" rx="3" fill="black" fill-opacity=".86"/>
<text x="740" y="365" font-family="Arial, sans-serif" font-size="24" fill="white">HV (dB)</text>
<image x="1110" y="24" width="66" height="78" xlink:href="data:image/svg+xml;base64,{logo}"/>
</svg>'''
(root/'docs/banner.svg').write_text(svg,encoding='utf-8')
# PNG companion makes the exact raster rendering easy to inspect locally.
canvas=Image.new('RGB',(1200,400),'#050708'); canvas.paste(im.convert('RGB'),(708,8))
canvas.save(root/'outputs/banner-raster-check.png')
print('Full HV footprint; nearest-neighbor pixels; no smoothing; 3x instead of prior ~9.4x crop.')
