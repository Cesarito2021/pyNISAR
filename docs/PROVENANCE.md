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
