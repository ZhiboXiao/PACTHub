"""Use the paper's corrected registered MIPs without increasing website timepoints.

Run with --paper-root pointing to paper_figures_website_aligned_20261027.
The supplied arrays are already oriented and registered: this importer only
selects real acquisitions and applies the paper's common XY crop. Quantitative
pixels never pass through windowing or image annotations.
"""
from pathlib import Path
import argparse
import copy
import csv
import gzip
import hashlib
import json
import struct

import numpy as np
from PIL import Image
from display_utils import scale_bar

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def edges(axis):
    return [float(axis[0] - (axis[1] - axis[0]) / 2),
            float(axis[-1] + (axis[-1] - axis[-2]) / 2)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper-root", type=Path, required=True)
    parser.add_argument("--qa-dir", type=Path, required=True)
    args = parser.parse_args()
    source_dir = args.paper_root / "source_data"
    source = source_dir / "dense_registered.npz"
    paper = read_json(source_dir / "temporal_paper.json")["wholebody"]
    records = read_json(source_dir / "dualband_10min_records.json")["records"]
    registration = read_json(source_dir / "dense_registration.json")
    data = read_json(ROOT / "data/temporal.json")
    series = next(s for s in data["series"] if s["id"] == "wholebody")
    other_series = copy.deepcopy([s for s in data["series"] if s["id"] != "wholebody"])
    protected = {p: digest(p) for s in other_series for p in
                 [ROOT / s["interactive_mips"]["url"], *[ROOT / f["image"] for f in s["frames"]]]}
    count = series["measured_timepoints"]
    assert count == len(series["frames"]) == 16
    assert len(records) == len(registration) == paper["count"] == 42
    times = np.array([r["elapsed_min"] for r in records], dtype="f8")
    selected = np.array([np.argmin(abs(times - t)) for t in np.linspace(times[0], times[-1], count)])
    assert len(set(selected)) == count and selected[0] == 0 and selected[-1] == len(times) - 1
    assert records[0]["group_id"] == paper["reference_acquisition"] == "20250103_172154"
    assert records[-1]["group_id"] == paper["last_acquisition"] == "20250103_173142"
    args.qa_dir.mkdir(parents=True, exist_ok=True)
    Image.open(ROOT / series["frames"][0]["image"]).save(args.qa_dir / "previous-first-frame.png")

    x0, y0, x1, y1 = paper["display_crop_xyxy"]
    with np.load(source) as z:
        pixels = np.ascontiguousarray(z["registered"][selected, y0:y1, x0:x1], dtype="<f4")
        valid = np.ascontiguousarray(z["valid"][y0:y1, x0:x1], dtype="u1")
        x, y = z["x"][x0:x1].astype("f8"), z["y"][y0:y1].astype("f8")
        source_shape = list(z["registered"].shape)
    assert np.isfinite(pixels).all() and pixels.min() >= 0 and valid.any()
    n, h, w = pixels.shape
    assert [h, w] == paper["display_shape_yx"]
    dx, dy = abs(float(np.median(np.diff(x)))), abs(float(np.median(np.diff(y))))
    low, cap = paper["display_window"]
    rendered = np.uint8(np.rint(np.clip((pixels - low) / (cap - low), 0, 1) * 255))
    # Independent exported paper PNGs must match before adding the website bar.
    for i, source_index in enumerate(selected):
        expected = np.asarray(Image.open(args.paper_root / f"assets/web/wholebody-t{source_index}.png"))
        assert np.array_equal(np.repeat(rendered[i, :, :, None], 3, axis=2), expected), source_index

    X, Y = np.meshgrid(x, y)
    defaults = []
    for roi in series["regions"]:
        a, b, c, d = roi["bounds_xy_mm"]
        region = (X >= a) & (X <= b) & (Y >= c) & (Y <= d)
        mask = region & valid.astype(bool)
        assert mask.any()
        values = pixels[:, mask].mean(1, dtype="f8")
        assert values[0] > 0
        roi.update(pixel_count=int(mask.sum()), common_valid_fraction=float(mask.sum() / region.sum()),
                   mean_linear=values.tolist(), relative_mean=(values / values[0]).tolist())
        yy, xx = np.where(region)
        defaults.append([int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1])

    transforms = []
    frames = []
    for i, source_index in enumerate(selected):
        record, tr = records[source_index], registration[source_index]
        assert record["group_id"] == tr["acquisition"]
        assert record["elapsed_min"] == tr["time_min"]
        matrix = np.vstack([np.array(tr["output_to_input_matrix"]), [0, 0, 1]])
        shift_mm = (np.array(tr["center_shift_px"]) * [dx, dy]).tolist()
        transforms.append(dict(acquisition_id=record["group_id"], rotation_z_deg=tr["angle_deg"],
                               center_shift_xy_pixels=tr["center_shift_px"], center_shift_xy_mm=shift_mm,
                               output_to_input_matrix=matrix[:2].tolist(),
                               input_to_reference_matrix=np.linalg.inv(matrix)[:2].tolist(),
                               feature_ncc_before=tr["feature_ncc_before"],
                               feature_ncc_after=tr["feature_ncc_after"]))
        path = ROOT / f"assets/images/temporal/wholebody-{i:02d}.webp"
        image, bar = scale_bar(Image.fromarray(rendered[i]), 1 / dx, 5, font_fraction=.06)
        image.save(path, lossless=True, method=6)
        assert np.array_equal(np.asarray(Image.open(path)), np.asarray(image))
        frames.append(dict(time_min=float(times[source_index]), image=path.relative_to(ROOT).as_posix(),
                           acquisition_id=record["group_id"], paper_index_0based=int(source_index),
                           image_sha256=digest(path), frames_1based=record["frames_1based"],
                           dataset_file=record["source_pa_file"].split("/Dataset/", 1)[1],
                           source_parameters_sha256=record["source_parameters_sha256"]))

    from temporal_codec import encode_preview
    packed, codec = encode_preview(pixels, valid)
    target = ROOT / 'assets/data/temporal/wholebody.q8.gz'
    target.write_bytes(packed)
    source_hash = digest(source)
    series["interactive_mips"] = dict(
        **codec, url=target.relative_to(ROOT).as_posix(), registered_source_sha256=source_hash,
        display_axis_edges_mm=dict(x=edges(x), y=edges(y)), default_rois_xyxy=defaults[:2],
        frame_order=[f["acquisition_id"] for f in frames], common_valid_pixels=int(valid.sum()),
        includes_scale_bar=False,
        definition="Paper-registered linear dual-band BP MIPs, globally quantized to 8 bits across all displayed timepoints, cropped without resampling. Shared-valid mask across the complete 42-point paper series. No display window, gamma or annotations in numerical data.",
    )
    series.update(frames=frames, duration_minutes=float(times[-1]), display_window=[low, cap],
                  display_rotation_deg=0, display_axis_transform="Already oriented in the paper's registered MIP coordinates; X decreases left to right, Y increases top to bottom.",
                  display_crop_xyxy=paper["display_crop_xyxy"],
                  extent_xy_mm=[*sorted(edges(x)), *sorted(edges(y))],
                  scale_bar=bar, source_sha256=digest(source_dir / "dualband_10min_mips.npz"),
                  time_origin="2025-01-03 17:21:54, the second original acquisition and the paper's reference time; injection time is not recorded.")
    series["registration"].update(
        reference_acquisition=frames[0]["acquisition_id"], transforms=transforms,
        common_valid_fraction=float(valid.mean()),
        common_valid_scope="All 42 paper acquisitions, then restricted to the common display crop",
        matrix_coordinate_frame="Uncropped 400 x 800 display-oriented MIP; pixel origin at its upper left",
        interpolation="Reuses the paper's single bilinear rigid warp; website crop and selection add no interpolation",
    )
    settings = ["bands_mhz", "filter_order_argument", "zero_phase", "sum_weights",
                "pre_addition_normalization", "speed_m_s", "frame_compounding", "added_gain",
                "postprocess_quantitative"]
    assert all(all(record[key] == records[0][key] for key in settings) for record in records)
    series["reconstruction"] = {key: records[0][key] for key in settings}
    series["paper_sync"] = dict(
        source_collection=args.paper_root.name, registered_file="source_data/dense_registered.npz",
        registered_sha256=source_hash, registered_shape_tyx=source_shape,
        source_records_sha256=digest(source_dir / "dualband_10min_records.json"),
        paper_display_sha256=digest(source_dir / "temporal_paper.json"),
        reconstructed_acquisitions=len(records), selected_indices_0based=selected.tolist(),
        selection="Nearest distinct actual acquisitions to 16 uniformly spaced elapsed-time targets, including both endpoints; timestamps and images are not temporally interpolated.",
    )
    assert other_series == [s for s in data["series"] if s["id"] != "wholebody"]
    assert all(digest(p) == old_hash for p, old_hash in protected.items())
    write_json(ROOT / "data/temporal.json", data)

    csv_path = ROOT / "data/temporal-readouts.csv"
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        other_rows = [row for row in reader if row["series"] != "wholebody"]
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for frame_index, frame in enumerate(frames):
            for roi in series["regions"]:
                writer.writerow(dict(series="wholebody", time_min=frame["time_min"], roi=roi["id"],
                                     mean_linear=roi["mean_linear"][frame_index],
                                     relative_to_first=roi["relative_mean"][frame_index]))
        writer.writerows(other_rows)
    summaries = read_json(ROOT / "data/registration-summary.json")
    summary = next(s for s in summaries if s["series"] == "wholebody")
    summary.update(
        timepoints=n, mean_feature_ncc_before=float(np.mean([t["feature_ncc_before"] for t in transforms[1:]])),
        mean_feature_ncc_after=float(np.mean([t["feature_ncc_after"] for t in transforms[1:]])),
        rotation_range_deg=[min(t["rotation_z_deg"] for t in transforms), max(t["rotation_z_deg"] for t in transforms)],
        max_center_shift_mm=max(float(np.linalg.norm(t["center_shift_xy_mm"])) for t in transforms),
        minimum_roi_valid_fraction=min(r["common_valid_fraction"] for r in series["regions"]),
    )
    write_json(ROOT / "data/registration-summary.json", summaries)
    report = dict(timepoints=n, total_website_timepoints=sum(len(s["frames"]) for s in data["series"]),
                  first=frames[0]["acquisition_id"], last=frames[-1]["acquisition_id"],
                  duration_minutes=series["duration_minutes"], selected_indices=selected.tolist(),
                  shape_tyx=list(pixels.shape), numerical_sha256=digest(target),
                  paper_pngs_exact_before_scale_bar=True, abdominal_data_and_images_unchanged=True,
                  registration=summary)
    write_json(args.qa_dir / "sync-report.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
