# Literature-based universal back-projection

**BP 实现说明：实际使用的内部 BP 重建程序属于保密内容，不对外分发。** 本公开包默认接入基于 Xu 和 Wang（2005）公开文献及其勘误编写的基础 UBP，保留 PAdata 和 JSON 接口，并在输出中记录公开算法的实际参数。FOV 分割与选择、声速评分与选择、信号处理、几何与 MB 实现均保留。详见 [公开 BP](PUBLIC_BP.md)、[文献来源](PUBLIC_BP_SOURCES.md) 与 [流程伪代码](PIPELINE_PSEUDOCODE.md)。

The BP baseline implements Xu and Wang's published **universal back-projection
(UBP)** equations. The numerical core is
[`literature_ubp.py`](pa_pipeline/backends/literature_ubp.py); the existing PAdata
and two-JSON contract is handled separately by
[`bp_adapter.py`](pa_pipeline/backends/bp_adapter.py).

## Public source

M. Xu and L. V. Wang, *Universal back-projection algorithm for photoacoustic
computed tomography*, Physical Review E **71**, 016706 (2005).
[DOI](https://doi.org/10.1103/PhysRevE.71.016706) ·
[Author-hosted PDF](https://coilab.caltech.edu/documents/26452/XuM_2005_Phys_Rev_E_71_016706.pdf) ·
[Author repository with erratum](https://authors.library.caltech.edu/records/8vsyr-zwm40).

Equations (20)–(22) supply the algorithm:

```text
b_i(t) = 2 [p_i(t) − t dp_i(t)/dt]
tau_i(x) = |x − s_i| / c
omega_i(x) = A_i n_i · (x − s_i) / |x − s_i|³
p0(x) = sum_i omega_i(x) b_i(tau_i(x)) / sum_i omega_i(x)
```

Here `n_i` points inward and `A_i` is a measurement-surface quadrature cell area.
Section III discusses normalization by available solid angle for partial views.
Section IV gives the uniform-sphere pressure used in the independent numerical
tests and executable demo. The erratum is DOI
[10.1103/PhysRevE.75.059903](https://doi.org/10.1103/PhysRevE.75.059903).
The 2007 erratum revises the proof around Eqs. (12)–(18); it does not change
the reconstruction results or the implemented Eqs. (20)–(22).

## Numerical implementation

These are explicit implementation choices:

- Second-order centered finite differences for the pressure derivative, with
  second-order one-sided endpoint stencils.
- Linear interpolation of `b_i` at the physical flight time.
- Equal surface-cell areas unless the numeric API receives explicit areas.
  A common area factor cancels in the normalized formula. This approximates
  quadrature; it does not infer a calibrated effective aperture for each detector.
- Inward geometric normals; no receiver directivity cutoff or apodization.
- Zero extension beyond the recording, retaining the geometric denominator.
- **Signed** output. Positivity and amplitude windows belong to visualization.
- Float64 geometry/sums and float32 signal term/output; NumPy or CuPy, bounded
  point and detector batches.

Measured PA signals are band limited and not a calibrated pressure impulse
response. The formula is applied to the recorded preprocessed signal, without
estimating detector-response deconvolution. Finite aperture, incomplete coverage
and equal-area quadrature remain approximations. Amplitudes are algorithm-dependent
signal units, not absolute pressure or absorption.

## PAdata / JSON compatibility

The existing data reader preserves frame indices, channel order, polarity,
bandpass, energy normalization, time crop, detector coordinates, geometry and grid.
Only `sample_metadata.json` and `reconstruction_parameters.json` supply parameters.
Detector coordinates may be embedded in the latter, as before.

The adapter constructs physical times from the published dataset clock:

```text
processed_sample_k_time_s = (k + 1 + predelay_samples) / sampling_frequency_hz
```

This is a dataset convention, not a UBP equation. The crop displacement is already
represented in the profile's predelay. The core receives physical times and has
no knowledge of predelay or frame indices.

Old reconstruction options can still be read. They do not select old BP rules:
`public_bp_adapter.source_options_replaced` records their original values, and
the output profile stores the actual UBP algorithm, linear interpolation, no
apodization and signed output. Analytic-signal input is rejected; this baseline
requires `analytic_signal=false`.

```sh
python -m pip install .
python reconstruct.py run "SAMPLE_DIR" --methods bp --backend cpu --out runs/ubp
```

For a compatible NVIDIA/CUDA 12 system:

```sh
python -m pip install cupy-cuda12x
python reconstruct.py run "SAMPLE_DIR" --methods bp --backend cuda --device 0 --out runs/ubp_gpu
```

No BP CUDA source or compiled custom kernel is required. MB retains its own solver.

## Standalone core

```python
from literature_ubp import ubp_volume

volume_zyx = ubp_volume(
    pressure_ct,             # real preprocessed [selected frame*channel, time]
    physical_time_s,          # [time], seconds, uniform sampling
    detector_xyz_mm,          # matching [selected frame*channel, 3]
    inward_unit_normals,      # matching measurement-surface normals
    [axis_x_mm, axis_y_mm, axis_z_mm],
    sound_speed_m_s=1495.0,   # read from the acquisition JSON
    backend="cuda",          # or "cpu"
)
```

Within the package, import from `pa_pipeline.backends.literature_ubp`.
`UBPProjector` evaluates many point sets after preparing the temporal term once.

## Verification and provenance

```sh
python -m unittest discover -s tests -v
python examples/public_bp_demo.py --backend cpu --out runs/sphere
```

Verification uses analytical functions, the paper's uniform-sphere signal,
CPU/GPU checks and the existing JSON input contract. Private-core outputs are
not numerical targets for this implementation.

The algorithm and discretization were specified from the cited publication in
this revision. Existing dataset I/O and geometry handling are reused for interface
compatibility. No third-party software source is copied. Earlier versions had
been inspected in this conversation, so this is a documented source-based rewrite,
not a claim of a formal clean-room development process.
