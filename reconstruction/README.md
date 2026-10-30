# PACTHub reconstruction pipeline

Reconstruct the standardized PA data using back-projection (BP) and the supplied V3 model-based (MB) solver. Field-of-view selection and sound-speed selection share the same input configuration and physical coordinates.


**BP implementation:** the actual internal BP reconstruction program is confidential and is not distributed. This package defaults to a public reference UBP based on Xu and Wang (2005), Eqs. (20)–(22), with the published erratum. It preserves the PAdata/JSON interface and records the effective public algorithm in each output. FOV, sound-speed selection and MB remain available. See [PUBLIC_BP.md](PUBLIC_BP.md), [sources](PUBLIC_BP_SOURCES.md) and [workflow pseudocode](PIPELINE_PSEUDOCODE.md).

[中文说明与完整参数表](README_CN.md) · [Website guide](https://pacthub.net/docs/algorithm-guide.html)

```text
PAdata + sample_metadata.json + reconstruction_parameters.json
    → validate → select frames and preprocess
    → select FOV → select sound speed
    → BP / MB → numerical 3D volumes, MIPs and effective parameters
```

## Input contract

Use the two JSON files delivered with each acquisition:

- `sample_metadata.json`: acquisition ID, FTC storage axes, array shape, data type and frame count.
- `reconstruction_parameters.json`: data paths, signal processing, frame indices, geometry, grid, sound speed and reconstruction settings. The published `1.0.0` and registered `1.0.0+starnet-rigid-v3` formats are supported.

The PA file is an HDF5 MAT/H5 array named `pa_data`, stored as `[frame, time, channel]`, with 1024 channels. Paths resolve relative to the parameter JSON. Sampling, signal scaling and channel conventions follow the recorded standardization.

Existing profiles reference a detector-coordinate MAT through `inputs.detector_file`. `configure --embed-detectors` copies those coordinates into `defaults.geometry.detector_xyz_mm`; subsequent reconstruction then needs only the PA file and the two JSON files. MB options are stored in `defaults.mb` in the same JSON.

## Install

Use Python 3.10 or newer. From this directory, install the base package:

```sh
python -m pip install .
```

The public BP runs on NumPy (CPU) or CuPy (CUDA). MB requires a CUDA-compatible PyTorch installation, Ninja and the CUDA compiler (`nvcc`). For a CUDA 12 environment, install `cupy-cuda12x`; install the PyTorch build appropriate to your GPU environment. Use `--backend cpu` for NumPy; the default backend is CUDA.

## Run

`SAMPLE_DIR` is a downloaded acquisition directory containing its two JSON files. First check the input, then generate a working profile and reconstruct:

```sh
python reconstruct.py inspect "SAMPLE_DIR"

python reconstruct.py configure "SAMPLE_DIR" --out profiles/sample --embed-detectors --with-mb --auto-fov --auto-speed

python reconstruct.py run profiles/sample --methods bp mb --out runs/sample --device 0
```

The CLI uses the public UBP by default. Optional local callbacks use the contract in BP_INTERFACE.md.

Omit `--auto-fov --auto-speed` to retain the recorded FOV and sound speed. `configure` creates a new pair of JSON files and retains the original PA data paths. Numerical settings are edited in that profile; command-line options choose paths, methods and the compute device. The installed command `pact-reconstruct` exposes the same interface.

Automatic FOV uses a large-FOV BP MIP to estimate the XY centre and long axis. Sound-speed selection evaluates the recorded candidate list with fixed frames, geometry and preprocessing. Candidate scores and masks are saved. Ambiguous candidates retain the recorded settings; selected values are saved in the output profile.

## Outputs

| Directory | Result |
|---|---|
| `BP/` | Recorded preprocessing and public literature UBP |
| `MB/` | V3 finite-disk forward/adjoint model and nonnegative iterative reconstruction |
| `BP_matched/` | Public UBP using the identical MB input |
| `profile/` | The two effective JSON files, ready to replay the selected parameters |
| `fov_detection/`, `speed_selection/` | Selection images, numerical scores and decisions when enabled |

Each reconstruction includes `mip.npz`, preview PNGs and execution records. With `defaults.output.save_volume=true`, `volume.h5` stores the float32 volume in **ZYX** order and physical axes in **mm**. MIP arrays use **YX** order. Preview normalization is separate from numerical output. BP and MB retain their respective operator-dependent amplitude units.

## Examples and verification

`examples/legacy_template` demonstrates the existing schema with a separate coordinate MAT. `examples/embedded_two_json` contains the same acquisition with embedded detector coordinates and MB settings. Both refer to acquisition `20241213_151351`: place its PA file at the example's recorded path or edit the paths. For another acquisition, start from that acquisition's own JSON pair.

```sh
python -m unittest discover -s tests -v
```

The 27 local tests cover analytical UBP, CPU/CUDA agreement, PAdata/JSON replay, geometry, MB input preparation and optional callback routing. Details are in `validation_report.json`.

The published metadata audit covers 1,469 acquisitions: 1,327 parameter records pass the interface checks and 142 retain their recorded unresolved status. This entry point reconstructs individual acquisition positions. Full-scan fusion requires explicit inter-position trajectories and fusion settings. Current reconstruction profiles use a single effective sound speed.

## Website and code maintenance

The repository root serves the static website. This directory contains the independently installable Python/CUDA package. GitHub Pages serves the code download and guides; reconstruction runs on a local machine or GPU server. RF datasets remain available through the website's Google Drive link.

After changing code, regenerate the small website download from the repository root:

```sh
python scripts/package_reconstruction.py
python scripts/package_reconstruction.py --check
```

The package script includes workflow source, the MB CUDA kernel, documentation, examples and interface tests. It rejects BP numerical cores. It records source hashes and excludes generated reconstructions, environments and RF data. Run the CPU tests and package check locally before uploading changes.
