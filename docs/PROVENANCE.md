# Source provenance

pyNISAR extracts NISAR modules from [PyGeoObserver](https://github.com/Cesarito2021/pygeoobserver),
local checkout commit `f54edd4f8f779752000f51c66c730fa29b21457a`. Original code: Copyright (c) 2026 Cesar.
The source checkout was left unchanged. Namespace and branding were updated;
the app, packaging, sample loader, discovery interface and command line are new.
The retained source license is GPL-3.0-only.

The six README figures and two bundled covariance/intensity subsets are existing
measured NISAR examples from the western Great Lakes, acquired 6 November 2025.
They are not observations from the manuscript's Amazon–Cerrado study area.
The dual example selects HH/HV from a quad GSLC acquisition. The quad example
uses all four measured channels of GCOV with an explicit reciprocity assumption.
See [source URLs and processing](figures/panels/sources.json).
Bundled covariance has already received the looks recorded in each manifest;
the demo re-derives descriptors without applying those looks a second time.
Original NISAR observations remain subject to NASA/ASF data attribution and terms.
No synthetic observations are presented as measured examples.

The polygon AOI reader adapts PyGeoObserver's `aoi.py`, retaining CRS validation
and adding explicit GeoPackage layer selection. Search queries the AOI bounding
box and filters candidate footprints against the polygon union.

## Banner and Python logo

`examples/render_banner.py` builds `docs/banner.svg` from the bundled GCOV
**VH.tif** (measured VH, not an HV alias), with a grayscale 2–98% dB display
stretch. The cropped decorative background is not a georeferenced map.
The black header and white lettering follow the owner's ALSdownloadeR reference.

The unmodified Python two-snakes logo was downloaded from the
[official Python logo page](https://www.python.org/community/logos/):
https://s3.dualstack.us-east-2.amazonaws.com/pythondotorg-assets/media/files/python-logo-only.svg.
It identifies implementation in Python. The Python logo is a trademark of the
Python Software Foundation; no endorsement is claimed or implied by its use.
