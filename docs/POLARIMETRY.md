# Native metric definitions

These definitions describe the extracted implementation. They do not establish
independent calibration or validate the manuscript's carbon model.

## Co/cross dual polarization

The covariance basis is `[HH, HV]` or `[VV, VH]`, without a √2 multiplier on
the cross channel. Let `a` and `b` be co- and cross-polarized mean powers and
`z = E(S_co · conjugate(S_cross))`. The covariance is `[[a,z],[conjugate(z),b]]`.
GSLC/RSLC form it from complex samples; GCOV reads the stored terms.

| Output | Definition |
|---|---|
| Measured powers | `a`, `b` under their actual channel names |
| span | `a+b` |
| ratio, cpr | `a/b`, `b/a` |
| difference, product | `a-b`, `a*b` |
| fraction | `b/(a+b)` |
| ndsi | `(a-b)/(a+b)` |
| rvi | `4*b/(a+b)` |

Where complete complex covariance exists, normalize its eigenvalues to
`p1 >= p2`, with `p1+p2=1`. Additional outputs are:

| Output | Definition |
|---|---|
| entropy | `−Σ p_i log₂(p_i)` |
| alpha | `Σ p_i acos(abs(v_i[0]))`, in degrees, in the stated C2 basis |
| dop | `p1-p2` |
| dprvi | `1-dop*p1` |
| prvi | `(1-dop)*b` |
| shannon_i | `2 ln(π e span/2)` |
| shannon_p | `ln(4 det(C2)/span²)` |
| shannon | `shannon_i+shannon_p` |

These are 18 layers including the measured powers. Diagonal-only GCOV yields
the 10 intensity layers, without inferred covariance descriptors.
Ratios are linear unless labeled as a display transform; Shannon units are nats.

## Full / quad polarization

All four measured channels must occur in the same frequency. The reciprocal
cross amplitude is `(HV+VH)/2`; the C3 basis is
`[HH, (HV+VH)/√2, VV]`. Thus `C22 = 2*HV_reciprocal` power.
The Pauli basis is `[(HH+VV)/√2, (HH−VV)/√2, (HV+VH)/√2]`.

The fixed 18-layer profile exports measured HH/HV/VH/VV; reciprocal HV power;
span; entropy; alpha; anisotropy; DoP; RVI; PRVI; three Pauli powers; two Shannon
components; and the measured HV/VH reciprocity residual.

With descending normalized Pauli T3 eigenvalues `p1,p2,p3`:

- Span is `trace(C3) = HH + 2*HV_reciprocal + VV`.
- H is `−Σ p_i log₃(p_i)`; alpha uses Pauli eigenvectors in degrees.
- Anisotropy is `(p2−p3)/(p2+p3)`.
- Barakat DoP is `sqrt(1−27*p1*p2*p3)`.
- RVI is `8*HV_reciprocal/span`, without clipping to one.
- PRVI is `(1−DoP)*HV_reciprocal`.
- Shannon intensity is `3 ln(π e span/3)`; polarization is `ln(27*p1*p2*p3)`.
- Reciprocity residual is `E|HV−VH|² / (E|HV|² + E|VH|²)`.

The full Shannon sum is not exported as a nineteenth layer. Original C4 covariance
and normalized C3 are retained by the small-window `process()` workflow for independent checks.
Chunked `process_tile()` / `process_batch()` save metric rasters without these
additional covariance archives to reduce storage. Positive repeated full-pol
eigenvalues leave alpha non-unique; it is recorded as NaN.

## Spatial and numerical support

Only complete finite sample blocks contribute. Added looks are boxcar averages;
no Refined Lee, terrain correction, noise subtraction or independent calibration
is applied by the native pipeline. Undefined ratios and finite Shannon entropy
for singular covariance are NaN. Zero power has undefined normalized descriptors.
Dual and full-pol H/alpha use different bases and must not be interchanged.
GSLC power is uncorrected mean |S|²; GCOV is used as stored, nominal gamma0.

Map products preserve their native CRS. RSLC exports radar pixel coordinates
and is never presented as a geocoded map. Equal window dimensions do not imply
equal geographic support across products. Descriptors derived from the same
covariance are mathematically dependent; their count does not describe a number
of independent physical measurements.

The legacy full-tile Colab pipeline and its Refined-Lee route are not part of
this initial extraction. Optional PolSARtools decompositions are separately
requested and require a compatible backend; experimental methods remain guarded.
