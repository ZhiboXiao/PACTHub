# BP integration interface

**BP implementation:** the actual internal BP reconstruction program is confidential and is not distributed. This package defaults to a public reference UBP based on Xu and Wang (2005), Eqs. (20)–(22), with the published erratum. It preserves the PAdata/JSON interface and records the effective public algorithm in each output. FOV, sound-speed selection and MB remain available. See [PUBLIC_BP.md](PUBLIC_BP.md), [sources](PUBLIC_BP_SOURCES.md) and [workflow pseudocode](PIPELINE_PSEUDOCODE.md).

Use the existing `PAdata`, `sample_metadata.json` and `reconstruction_parameters.json` contract. The literature UBP is connected by default. A different local BP can be registered as a Python callable; acquisition parameters continue to come from the two JSON files.

```python
from pa_pipeline.bp_interface import set_bp_backend
from pa_pipeline.workflow import run
from my_local_backend import reconstruct

set_bp_backend(reconstruct)
run('SAMPLE_DIR', 'runs/sample', methods=('bp',), backend='cpu')
```

The callback signature is:

```text
reconstruct(data, sensors, cfg, backend='cuda', speed=None,
            volume_sink=None, normals=None) -> (mip_yx, [axis_x, axis_y, axis_z])
```

- `data`: prepared real signal `[selected frame 脳 channel, time]`.
- `sensors`: matching `[selected frame 脳 channel, 3]` coordinates in mm.
- `cfg`: validated parameters, including physical grid, signal clock, sound speed and projection support.
- `normals`: transformed physical receive directions when registration supplies them.
- `speed`: optional sound-speed sweep override in m/s; otherwise use the JSON speed.
- `volume_sink`: when supplied, fill the provided float32 `[z,y,x]` array.
- Return the numerical XY-MIP and three physical coordinate axes in mm.

BP, automatic FOV and sound-speed selection use the public UBP by default. Calling `set_bp_backend(None)` explicitly disables BP. Data inspection and parameter preparation remain available. MB with recorded FOV and sound speed runs independently; its optional `BP_matched` comparison is skipped when no BP callback is available.

The flow is summarized in [PIPELINE_PSEUDOCODE.md](PIPELINE_PSEUDOCODE.md). Image and video assets on the website retain their original provenance.

## Keep the existing CLI

Save the following as a local `local_runner.py` alongside your installed workflow:

```python
from pa_pipeline.bp_interface import set_bp_backend
from pa_pipeline.cli import main
from my_local_backend import reconstruct

set_bp_backend(reconstruct)
main()
```

Then use the existing commands with `python local_runner.py run ...`. This runner connects your local code; it does not implement BP. `inspect` and `configure` can still use `python reconstruct.py` directly.
