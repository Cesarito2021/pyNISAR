"""Bounded GSLC intensity previews; no sigma0 correction or Refined Lee."""
from pathlib import Path
import json
import uuid

import h5py
import numpy as np
import rasterio
from affine import Affine
from rasterio.warp import transform as transform_coordinates


def _validate(channels, window_size, looks):
    if type(window_size) is not int or not 1 <= window_size <= 4096:
        raise ValueError("window_size must be an integer between 1 and 4096.")
    if len(looks) != 2 or any(type(v) is not int or v < 1 for v in looks):
        raise ValueError("looks must contain two positive integers.")
    if not channels or len(set(channels)) != len(channels) or not set(channels) <= {"HH", "HV", "VV", "VH"}:
        raise ValueError("Select distinct HH, HV, VV or VH channels.")


def _grid(h, channels):
    base = "/science/LSAR/GSLC/grids/frequencyA"
    if base not in h:
        raise ValueError("Preview requires a frequencyA GSLC geocoded grid.")
    g = h[base]
    if any(c not in g for c in channels):
        raise ValueError("Selected polarization is absent from the GSLC grid.")
    x, y = np.asarray(g["xCoordinates"]), np.asarray(g["yCoordinates"])
    dx, dy = float(g["xCoordinateSpacing"][()]), float(g["yCoordinateSpacing"][()])
    if len(x) < 2 or len(y) < 2 or dx == 0 or dy == 0:
        raise ValueError("Invalid geocoded grid.")
    if not np.allclose(np.diff(x), dx) or not np.allclose(np.diff(y), dy):
        raise ValueError("Nonuniform grid is not supported.")
    crs = rasterio.crs.CRS.from_epsg(int(g["projection"][()]))
    return g, x, y, dx, dy, crs


def _center_pixel(center, x, y, dx, dy, crs):
    if center is None:
        return len(y)//2, len(x)//2
    lon, lat = center
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("center must be longitude, latitude.")
    xx, yy = transform_coordinates("EPSG:4326", crs, [lon], [lat])
    cf, rf = (xx[0]-x[0])/dx, (yy[0]-y[0])/dy
    if not (-0.5 <= cf < len(x)-0.5 and -0.5 <= rf < len(y)-0.5):
        raise ValueError("Requested center is outside the scene.")
    return int(np.floor(rf+0.5)), int(np.floor(cf+0.5))


def _window(center, size, looks, x, y, dx, dy, crs):
    row, col = _center_pixel(center, x, y, dx, dy, crs)
    nr = min(size, len(y)) // looks[0] * looks[0]
    nc = min(size, len(x)) // looks[1] * looks[1]
    if nr == 0 or nc == 0:
        raise ValueError("Window is smaller than the selected looks.")
    r0, c0 = max(0, min(row-nr//2, len(y)-nr)), max(0, min(col-nc//2, len(x)-nc))
    affine = Affine(dx*looks[1], 0, x[c0]-dx/2, 0, dy*looks[0], y[r0]-dy/2)
    return [r0, c0, nr, nc], affine


def _complex_window(ds, window, shape):
    if ds.shape != shape:
        raise ValueError("Channel and coordinate dimensions differ.")
    r0, c0, nr, nc = window
    raw = ds[r0:r0+nr, c0:c0+nc]
    if raw.dtype.names:
        if not {"r", "i"} <= set(raw.dtype.names):
            raise ValueError("Unsupported complex compound type.")
        raw = raw["r"].astype("float32") + 1j*raw["i"].astype("float32")
    if not np.iscomplexobj(raw):
        raise ValueError("GSLC samples must be complex.")
    return raw.astype("complex64")


def _intensity(ds, window, looks, shape):
    raw = _complex_window(ds, window, shape)
    _, _, nr, nc = window
    power = np.abs(raw.astype("complex64"))**2
    # Invalid samples propagate; valid zeros remain valid.
    power[~np.isfinite(power)] = np.nan
    return power.reshape(nr//looks[0], looks[0], nc//looks[1], looks[1]).mean(axis=(1, 3))


def _save_layer(target, power, channel, crs, affine):
    valid = power[np.isfinite(power)]
    if valid.size == 0:
        raise ValueError(f"No finite samples in {channel}; select another center.")
    with rasterio.open(target, "w", driver="GTiff", width=power.shape[1], height=power.shape[0],
                       count=1, dtype="float32", crs=crs, transform=affine, nodata=np.nan,
                       compress="deflate") as dst:
        dst.write(power, 1)
        dst.set_band_description(1, f"{channel}: mean(abs(S)^2), uncorrected intensity")
        dst.update_tags(quantity="mean_abs_S_squared", radiometric_correction="none", filter="boxcar")
    return {"file": target.name, "shape": list(power.shape), "finite_fraction": float(valid.size/power.size),
            "nonzero_fraction": float(np.count_nonzero(valid)/valid.size),
            "min": float(valid.min()), "max": float(valid.max()), "mean": float(valid.mean())}


def preview_gslc(source, output, *, channels=("HH", "HV"), center=None, window_size=512, looks=(6, 3)):
    """Export mean(abs(S)**2) GeoTIFFs from a bounded GSLC window.

    center: (longitude, latitude), or None for grid center.
    window_size: maximum source pixels per axis, up to 4096.
    looks: (rows, columns); incomplete edge looks are discarded.
    source: path (including mounted Drive) or seekable binary file.
    Remote HDF5 access transfers chunks/metadata, not zero network traffic.
    Outputs are uncorrected intensity, not sigma0; no Refined Lee is applied.
    """
    channels = tuple(channels)
    _validate(channels, window_size, looks)
    with h5py.File(source, "r") as h:
        g, x, y, dx, dy, crs = _grid(h, channels)
        window, affine = _window(center, window_size, looks, x, y, dx, dy, crs)
        run = Path(output) / ("preview-" + uuid.uuid4().hex)
        run.mkdir(parents=True)
        report = {"status": "running", "quantity": "mean_abs_S_squared", "radiometric_correction": False,
                  "filter": "boxcar_multilook_only", "source": str(source) if isinstance(source, (str, Path)) else "seekable_HDF5",
                  "window": window, "looks": list(looks), "channels": list(channels), "layers": {}}
        manifest = run / "manifest.json"
        manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
        try:
            for channel in channels:
                power = _intensity(g[channel], window, looks, (len(y), len(x)))
                report["layers"][channel] = _save_layer(run/f"intensity_{channel}.tif", power, channel, crs, affine)
            report["status"] = "complete"
        except Exception as exc:
            report.update(status="failed", error=str(exc))
            raise
        finally:
            manifest.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return run
