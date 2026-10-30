# PACTHub

A structured data foundation for photoacoustic AI: standardized PAdata, a unified JSON parameter interface, BP / MB reconstruction and quantitative benchmarks.

## Dataset access and citation

The [representative sample subset on Zenodo](https://doi.org/10.5281/zenodo.23496053) contains 45.28 GB of data and is licensed under CC BY 4.0. The [Google Drive dataset](https://drive.google.com/drive/folders/1zBrduTKe5gnsNmlOfsDCgB9y5JTp5x3b) remains available.

**If you use this dataset, please cite both the data record and the dataset paper.**

1. Xiao, Z. (2026). *PACTHub* [Data set]. Zenodo. https://doi.org/10.5281/zenodo.23496053 — [BibTeX](assets/citations/pacthub-dataset.bib).
2. **Dataset paper — arXiv forthcoming.** Its link and citation will be added when published.

The bilingual resource section shows both citation slots. Metadata lives in `data/site-config.json` under `dataset_citations`. To publish the paper entry, set `paper.status` to `published` and fill `paper.title`, `paper.url` and `paper.citation`; optionally set `paper.bibtex_file`. The frontend then displays the linked paper and copy action in the reserved slot.

The homepage foregrounds the structured dataset. Section 04 keeps three compact, equal-height columns for structured input, BP / MB processing, and numerical evaluation. Below those columns, Section 04 presents a 28-second native SVG workflow animation directly under the `reconstruction_parameters.json` heading, followed by the FOV/sound-speed and Q video previews. Its opening sequence animates the left-hand selection and JSON reveal together with the right-hand operation: `signal` reveals the 0.5–6 MHz passband; `frames` illuminates the 20 selected exposures in order; `grid` creates the physical volume; `geometry` translates and orients it. The first full sequence plays once, then changes in place to interactive exploration. Clicking a group replays that operation once; replay restarts the complete introduction. All four parameter objects are included verbatim from the shipped example, with scrollable syntax-highlighted values and expandable large arrays. Geometry is a schematic of the configured pose; `grid.center_mm` is explicitly identified as a grid field. Right-hand captions contain only step labels, units and essential values. The animation pauses offscreen and in hidden tabs; reduced motion starts with the interactive state and supports explicit replay. There is no reconstruction or MB chapter.

Rebuild the data with `python scripts/build_parameter_explorer.py`. `data/parameter-explorer.json` records the source hash; the site validator checks complete object equality against that source.

## Reconstruction code and website

The [data-processing workflow](reconstruction/README.md) connects **PAdata → preprocessing → FOV selection → sound-speed selection → reconstruction** using each acquisition's `sample_metadata.json` and `reconstruction_parameters.json`. The public package supplies interfaces, processing, pseudocode and MB; the default BP is the [public literature UBP](reconstruction/PUBLIC_BP.md). **The actual internal BP program is confidential and is not distributed.** [Download the source-only package](assets/downloads/pacthub-workflow-v1.4.0.zip) or read the [Chinese parameter guide](reconstruction/README_CN.md).

| Location | Purpose |
|---|---|
| `index.html`, `assets/`, `data/` | Static website, specimen displays and interactive temporal measurements |
| `docs/` | Readable, bilingual website guides |
| `reconstruction/` | Independently installable reconstruction code, CUDA kernels, examples and tests |
| `assets/downloads/` | Small code download generated from `reconstruction/` |
| Zenodo / Google Drive | Archived representative subset / PA datasets and acquisition metadata |

GitHub Pages serves the website and downloads. Python/CUDA reconstruction runs on a local machine or GPU server. Section 04 places a labelled GitHub pipeline-code link in the section heading, above all three workflow steps. Section 05 provides dataset access and citation information. Source edits remain in `reconstruction/`; run `python scripts/package_reconstruction.py` to refresh the website ZIP. Run CPU tests and the package check locally before uploading changes. Numerical outputs are kept outside the website assets until explicitly prepared for display.

Section 04 pairs two static video previews: **FOV and sound-speed selection** (32 seconds) and **Q calculation** (51 seconds). Clicking a preview opens the complete film in a dialog with bilingual captions below the image, chapter navigation, a scrubber, restart and fullscreen controls. Closing the dialog pauses and unloads the movie and returns keyboard focus to its preview. Full movies load only after a click.

The calibration film uses acquisition `20241213_151351` and the same 20 BP exposures throughout. After scout localization, all 23 sound-speed candidates from 1488 to 1499 m/s are reconstructed from PA data on the recorded final **40 × 80 × 20 mm FOV**, with its centre and **−12.145° Z correction**. The CUDA run uses a 400 × 800 × 200 grid (approximately 0.10 mm spacing) on a local RTX 4080. Full-MIP normalized-gradient scores are recomputed by the published pipeline; their maximum is 1492.0 m/s. Full images, corresponding insets and all scores use that final coordinate system. Display windows are shared across speeds. `data/calibration-video.json` records input hashes, frames, grids, settings, scores and captions.

Recompute the speed cache with `python -X utf8 scripts/reconstruct_calibration_sweep.py --parameters FINAL_PARAMETERS_JSON --pa-file PA_DATA_H5 --detector-file DETECTOR_MAT --density 10 --out ALIGNED_SWEEP`. Render it with `python -X utf8 scripts/build_calibration_video.py --source-root SCOUT_CACHE --aligned-sweep ALIGNED_SWEEP --qa-dir LOCAL_QA`. The scout cache contains `localization20/{mips.npz,parameters.json}` and `fov_selection.json`; the aligned sweep contains `mips.npz`, `parameters.json` and `result.json`. Rendering produces a 1280 × 720 H.264 movie and preview image. Both workflow films use `assets/js/pipeline-films.js` and `assets/css/pipeline-films.css` for the shared viewer.

The static site keeps the cinematic dark visual system and uses a consistent set of scientific image views. All eight representative specimens offer depth and intensity MIPs and oblique 3D views, with calibrated scale bars and acquisition IDs. Two registered time series link image regions to progressively revealed intensity traces. One 51-second video presents six Q chapters, from the manuscript's 3D control to the measured-mouse calculation. Captions and playback controls sit below the image, keeping every formula and data panel visible.

## Run locally

```sh
python scripts/serve.py --port 8765
```

Open `http://127.0.0.1:8765`. The preview server supports HTTP byte ranges for video chapter seeking. No frontend dependencies or build step are required.

## Homepage volume animation

The released Figure 5b mouse volume lies at 30 degrees from upper left to lower right in a large, centred diagonal composition, with head and tail reversed relative to the initial compact view, and rolls around its longitudinal Y axis by ±12 degrees for two slow cycles. The 12-second loop keeps the entire specimen visible behind the title and **1,464 samples / 99,810 exposures** statistics. The lower-left gradient supports the copy. The desktop encode uses a 1920 × 1320 canvas to reduce letterboxing in the tall hero section. Desktop and mobile encodes use the same numerical source and display window; physiological motion appears in Section 01.

Build with `python scripts/build_home_orbit.py --source FRONTAL_VIEW_MAT --work-dir LOCAL_QA`. `data/hero-story.json` records the release attribution, source hash, orientation, display settings and output hashes.

## Three overview films

Section 01, **See imaging in action**, automatically cycles through three films in one wide video stage: structure, motion, then rotation compounding, returning to structure after the final film. The tabs and keyboard arrow keys switch films immediately; the playlist then continues from that selection. Pausing is preserved across selections, playback pauses offscreen, and reduced-motion preferences disable autoplay.

- **Structure, in detail:** the existing 24-second scan-and-rotation orbit and vascular zoom, from `20260114_192341_Scan1`. The 3D input is the equal-weight sum of 1.44–5.76 MHz and 0.5–8 MHz BP volumes. `data/overview-film.json` records the source and display envelope.
- **Anatomy in motion:** the homepage grayscale/depth physiological film with its established fixed temporal-union display masks. The depth panel has its RGB [12, 10, 0] background pedestal removed; the exterior becomes black. All 474 original frames and the 15.8-second timing are retained. `data/motion-cutout.json` records the source and mask hashes. Rebuild with `python scripts/build_motion_cutout.py --masks DISPLAY_MASKS_NPZ --qa-dir LOCAL_QA`.
- **Rotation compounding:** twenty nested BP reconstructions of leaf phantom `20241115_104329`, using consecutive exposures 1–20. A large axial MIP sits on the left; the right column stacks a rotating hemispherical-array schematic above a 4 × 5 exposure matrix. All twenty cells remain illuminated during the final result. Sound speed (1495 m/s), 0.5–6 MHz order-3 zero-phase bandpass, geometry and FOV are inherited from the sample parameters. The display window is fixed across the sequence; there is no additional filter or gain. `data/leaf-compounding.json` records the physical bounds, settings, layout and output hashes.

`data/overview-library.json` lists the three films and their hashes. The leaf sequence is reconstructed on the user-specified Zhejiang Lab GPU server with `scripts/reconstruct_leaf_sequence.py`. Prepare the 18-second film using `python scripts/build_leaf_film.py --work-dir LOCAL_QA`, with numerical projection files in `LOCAL_QA/leaf-results` and `InterVariable.ttf` in `LOCAL_QA`. `scripts/build_overview_library.py` invokes the same builder. The temporal explorer remains in Section 03.

## Interface typography and colour

All website text, including SVG/chart labels and numeric controls, uses locally hosted Inter, with a system sans-serif fallback for Chinese. `assets/css/linear-theme.css` uses the official Linear dark palette: near-black and graphite surfaces, gray-white text, and silver selection accents. Temporal traces use grayscale and distinct solid/dashed line styles. Scientific depth colour maps retain their calibrated meanings. The font licence is included in `assets/fonts`.

## Temporal explorer

- Whole-body series: 16 actual acquisitions sampled from the paper's corrected 42-point sequence, 0–9.8 min (`20250103_172154` to `20250103_173142`).
- Abdominal 800 nm series: first 20 timepoints, 0–19.23 min.
- All 36 displayed timepoints are rigidly aligned to their sequence's first frame (Z rotation and XY translation).
- Interactive rectangular regions drawn, moved or resized directly on the MIP, with up to six simultaneous traces. Means use calibrated 8-bit linear BP previews over pixels valid at every timepoint.
- A single bilinear resampling per frame; no scaling, deformable registration or framewise intensity normalization.
- The whole-body mouse reuses the paper's registered, head-up dual-band BP MIPs, common crop and linear display window. The website selects real acquisitions nearest 16 evenly spaced time targets; images and timestamps are not interpolated. It sums the 1.44–5.76 MHz and 0.5–8 MHz BP volumes before projection, with unit weights and no additional gain. The first selected acquisition defines zero time.
- One fixed linear display window per sequence; readouts support a.u. and ratios to the first frame.
- Play/pause, restart, frame scrubbing, playback speed, region visibility and bilingual labels.
- Actual acquisition times determine the horizontal plot coordinates. Playback advances by sampled frame; line segments connect measured points without fitted values.

Region names denote image locations. The readouts are regional photoacoustic intensity measurements, not absolute organ-specific concentration measurements.

## Data and provenance

`data/samples.json` contains sample metadata and views. `data/temporal.json` describes the measured frames, interactive MIP stacks and reference regions; `data/temporal-readouts.csv` retains the four original reference-region measurements. `data/display-provenance.json` records source and display hashes.

Display assets derive from the audited paper figure sources. Preparation uses NumPy, SciPy, OpenCV, Pillow, h5py and VTK; the video also uses FFmpeg. Run the complete sequence so registration and scale annotations remain synchronized:

```sh
python scripts/prepare_showcase.py --source-root PATH_TO_AUDITED_FIGURES
python scripts/register_temporal.py --source-root PATH_TO_AUDITED_FIGURES --qa-dir LOCAL_QA
python scripts/export_temporal_mips.py --registered-dir LOCAL_QA --flip-abdominal
python scripts/build_sample_views.py --source-root PATH_TO_AUDITED_FIGURES --scan-volume SCAN_PROCESSED_H5 --qa-dir LOCAL_QA
python scripts/build_additional_samples.py --dataset-root PATH_TO_WXH_DATASET --paper-root PATH_TO_AUDITED_FIGURES --official-root PATH_TO_EXTRACTED_3DPANOPACT_RELEASE --qa-dir LOCAL_QA
python scripts/build_q_video.py --evidence-root PATH_TO_MANUSCRIPT_Q_EVIDENCE --qa-dir LOCAL_QA
python scripts/build_q_mouse_video.py --evidence-root PATH_TO_MANUSCRIPT_Q_EVIDENCE --volume-root PATH_TO_DELIVERY_RECON --qa-dir LOCAL_QA
python scripts/assemble_q_video.py --qa-dir LOCAL_QA
python scripts/build_guides.py
python scripts/validate_site.py
node --check assets/js/app.js
node --check assets/js/temporal.js
node --check assets/js/temporal-quant-worker.js
node --check assets/js/q-video.js
node --check assets/js/overview-film.js
```

The preparation script expects `author_volume_display.json`, `specimen_volume_display.json`, `dynamic_display.json`, the associated display PNGs, and the two source `mips.npz` files. Source RF and volumes are not part of this website checkout. Physical coordinates and display choices are recorded per sample; unknown metadata are null.

The scan display volume is exported by `prepare_scan_display_volume.py` using the established manuscript processing: unit-weight sum of two BP volumes, then 0.7 normalized raw + 0.3 normalized Frangi. All three scan views share a tighter XY crop and 2-degree alignment. Scale bars use coordinate axes for scan/leaf/hand/time series; the author mouse's display scale is transferred from the original manuscript's labelled 5-mm bar through the matched volume-box projection. Its absent native axes remain null. Calibration details are in sample metadata.

`data/registration-summary.json` contains alignment diagnostics; transforms and acquisition IDs are recorded for every timepoint in `data/temporal.json`. `data/q-calculation.json` stores the exact formula, support settings, source-code hashes and recomputed Q/PSNR/full-image SSIM/L1 scores. The video draws MIPs for illustration; all its metrics are calculated in 3D.

GitHub Pages serves the main branch. Feature changes are reviewed through pull requests. Full dataset access, licence and formal citation are managed in `data/site-config.json`.

## Additional specimens and measured-mouse Q

The gallery uses three additional volumes from the [official 3D-PanoPACT v3 release](https://doi.org/10.6084/m9.figshare.28443374.v3): `whole_brain_STINT_processed.mat` (Fig. 3), `backside_view_time_point.mat` (Fig. 5d), and `liver_singleframe_processed.mat` (Fig. 2a). These provide whole-brain, dorsal whole-trunk and single-exposure liver views. Depth, grayscale and oblique 3D views are regenerated from the numerical volumes with one shared XYZ crop, linear window and fixed camera. The whole-trunk volume is oriented to the manuscript using a 180-degree XY rotation and retains the full released 250 × 875 × 375 (Z × Y × X) grid. The liver is flipped up-down along Y after its shared XYZ selection, so the same selected voxels and physical bounds appear consistently in all three views. The liver replaces the ex vivo brain specimen. The square-target phantom (20230920_150300) uses its measured 20-exposure BP volume, tightly cropped to include three targets of different sizes; all three views share the same XYZ extent.

The release is credited to Xuanhao Wang, Yuqian Meng and Xiali Gao under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Related article: [Nature Communications 16, 10077 (2025)](https://doi.org/10.1038/s41467-025-65054-x). The brain acquisition field shows `20230705_160311`, linked to the standardized dataset file `WXH/Animal/20230705/20230705_160311/PA_Data/Data_20230705_160311_PA.mat` (800 nm). Its detail note identifies the displayed result as the 3D-PanoPACT mousebrain multi-wavelength volume. This links a same-specimen dataset acquisition for lookup; it does not assign that single-wavelength RF as the unique source of the released composite. The dorsal trunk and liver cards and details show the first and last real standardized dataset IDs as `first ID - last ID`: 8 acquisitions from 20230908 (p1–p4), and 15 acquisitions from 20230112 (pos1_LIVER–pos5). These are explicitly labeled candidate acquisitions, because the official release has no verified acquisition/frame manifest. The complete ID lists, exact filenames and relative dataset paths remain in `acquisition_groups`; any listed ID or filename can be used in sample search. Figure-linked release IDs remain in the provenance metadata. The brain is labeled as a multi-wavelength compound following the dataset author's interpretation; its wavelength combination and weights remain unspecified. The dorsal trunk is labeled as a scan compound. These names identify experiment families, without assigning a unique RF frame. Their native physical axes are absent. Brain display spacing (0.04 mm) is transferred from the matched local BP grid (53 inliers; independently estimated X/Y pitches 0.040049 and 0.040006 mm). Whole-trunk display spacing (approximately 0.0833 mm) is transferred from the original Fig. 5d 5-mm bar after accounting for the PowerPoint image crop (1,514 feature correspondences). The liver display spacing (approximately 0.0564 mm) is transferred through the Fig. 2a 5-mm bar and volume-box projection. These use an isotropic display-grid assumption; these are display calibrations, not native acquisition coordinate records. The shared depth bar remains relative (0–1).

`scripts/additional_specimen_views.json` records source variables, physical transforms, XYZ bounds, windows, attribution and scale calibration. `data/additional-specimens.json` records rendered settings and source SHA-256 hashes. Rebuild with `scripts/build_additional_samples.py`, supplying the extracted official release through `--official-root`.

The orbit-and-zoom film has no scale annotation; the compounding and time-series films include calibrated 5-mm bars. Sample views use lower-right HTML overlays whose lengths track the actual image-to-screen scale, including responsive cards and detail dialogs.

Sample details show the three views and concise acquisition metadata. Click an image or **Enlarge image** for a full-window viewer: scroll or use +/− to zoom from 1× to 8×, drag to pan, and choose **Fit to window** to reset. The three views can be switched inside the viewer. Its ruler stays in the lower-right corner and updates with magnification. Provenance and sample-file sections are omitted from the dialog; numerical records remain in the repository.

Chapter 06 of `assets/media/q-calculation.mp4` begins at 35 seconds and presents the 16-second measured-mouse calculation. The reference is displayed as **GT** and comes from the manuscript 50-exposure BP volume; the corresponding reconstruction is displayed as **Test image**. Frame counts are omitted from the film and its captions; acquisition provenance remains in the numerical record. The recomputed 3D masks and metrics match the manuscript: Q = 82.5347574, Dweak = 0.7871648 and Dstrong = 0.8653825. The original shared display window and head-at-top orientation are retained. `data/q-mouse-calculation.json` records the source hashes, parameters and scores. Rebuild with `scripts/build_q_mouse_video.py`, then join the unchanged theory segment with `scripts/assemble_q_video.py`. The six chapters and bilingual captions are recorded in `data/q-video.json`.

The dataset card in Resources opens the author-provided [Google Drive folder](https://drive.google.com/drive/folders/1zBrduTKe5gnsNmlOfsDCgB9y5JTp5x3b). The destination and button labels are configured in `data/site-config.json`.

## Interactive temporal regions

Section 03 supports drawing, moving, corner resizing, hiding and deleting up to six regions. Arrow keys move a focused box; Shift changes the step from one to ten pixels. Selection and playback share the displayed coordinate system. Two example regions are supplied, and each sequence retains its selected regions while switching views. Curves show all measured timepoints faintly, with progressive highlighting during playback.

The browser loads gzip-compressed 8-bit linear previews (`*.q8.gz`): 16 whole-body frames at 650 × 320 pixels (1.82 MB) and 20 abdominal frames at 800 × 400 pixels (3.88 MB). One scale and offset cover the complete intensity range of each sequence, with no clipping or spatial/temporal subsampling. Display images and original float32 sources are retained. PAM2 uses a 36-byte little-endian header: magic `PAM2`, uint32 frame count/height/width/bits, then float64 scale and offset. Uint8 pixel codes are followed by the shared-valid uint8 mask. A linear intensity is `code × scale + offset`.

The selected sequence loads when the temporal section approaches the viewport. SHA-256 verification precedes exact uint32 summed-area indexing in a Web Worker; ROI means are decoded back to linear intensity. Every timepoint uses the same valid pixels. Display windows and scale-bar pixels never enter the measurement. The calibration and payload hashes are in `data/temporal.json`; each sequence loads once per page session. The two default ROI traces differ from float32 by less than 0.02% across these sequences. Small 4 × 4 regions are more sensitive: the largest relative-trace error in the seeded 200-ROI-per-size audit was 2.68%. These are web preview readouts; manuscript calculations retain the original floating-point inputs. Rebuild and audit with `python scripts/compact_temporal_mips.py --report LOCAL_REPORT_JSON`.

`scripts/sync_wholebody_temporal.py --paper-root <paper-output-directory> --qa-dir <audit-directory>` imports the corrected paper series. It preserves the 16-point website count, checks all selected display images against the paper PNGs, quantizes the registered pixels for web previews without further resampling, recalculates reference ROI readouts from the float originals and preserves the abdominal sequence. `paper_sync` metadata records source hashes and selected acquisition indices. The interactive overlay follows each sequence's actual image aspect ratio and physical pixel edges.

The abdominal 800 nm sequence is flipped vertically, with selection coordinates and numerical pixels transformed together; its 5-mm bar stays at the lower right. All mouse panels in Q chapter 06 are also flipped vertically. The 3D Q calculation and scores are unchanged. Direct JSON/CSV links and sample-metadata export buttons have been removed from the public interface and guides. Google Drive access, readable guides, video download and publication citations remain available.

`data/official-volume-sources.json` lists each released numerical volume, its MAT variable, native HDF5 dimensions, file size, SHA-256 and official source URL. These records identify the volume arrays used to render the views.

## Related publications

Section 06 presents three verified papers: Wang et al., *Nature Communications* 16, 10077 (2025), DOI `10.1038/s41467-025-65054-x`; Huang et al., *Advanced Imaging* 3(5), C00004 (2026), DOI `10.3788/AI.2026.10028`; and Meng et al., *BME Frontiers* 7, 0327 (2026), DOI `10.34133/bmef.0327`.

Each preview is the complete first page rendered from its published PDF. Click to open the page, then click or press Enter to toggle enlargement. The cards provide the full title, authors, journal, year, volume/article number, DOI, a copyable full citation and BibTeX. All three first pages are credited under CC BY 4.0. `data/publications.json` records verified metadata, source URLs and PDF/image hashes; citation files are in `assets/citations/`. Rebuild with `python scripts/build_publications.py --panopact PACT_PDF --panopaus PAUS_PDF --liver LIVER_PDF`.
