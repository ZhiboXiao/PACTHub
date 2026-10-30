# PAdata workflow pseudocode

```text
INPUT PAdata, sample_metadata.json, reconstruction_parameters.json

validate acquisition identity, shape, frame indices, units and recorded parameters
read the selected PAdata frames in the recorded order
apply the recorded signal scaling, polarity, energy normalization, filtering and crop
construct detector coordinates and apply recorded frame transforms

IF automatic FOV is requested:
    scout ← public literature UBP on the large physical grid
    contrast ← positive local contrast in the scout MIP
    support ← threshold, connected regions and morphological cleanup
    center, orientation, bounds ← geometry of the effective support
    apply valid choices and save the segmentation and decision

IF automatic sound-speed selection is requested:
    keep frames, geometry, signal preprocessing and depth support fixed
    reconstruct each recorded candidate speed with the public literature UBP
    score the numerical candidate MIPs over shared support
    select the valid optimum and save scores and parameters

save the effective two-JSON replay profile

IF BP is requested:
    pass prepared signals, geometry, physical grid and clock to the public UBP backend
    save its numerical ZYX volume, YX-MIP, axes and parameter record

IF MB is requested:
    prepare the recorded matched temporal filter and support mask
    reconstruct with the finite-disk forward/adjoint iterative MB solver
    save the numerical volume and iteration history
    IF BP has not been explicitly disabled:
        reconstruct BP_matched with the identical MB input
    ELSE:
        record BP_matched as skipped

generate display previews from the numerical outputs
OUTPUT volumes, projections, axes, effective parameters and processing records
```

The pseudocode describes orchestration. The public package includes the literature UBP reference. The actual internal BP program is confidential and is not distributed.
