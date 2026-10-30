"""Render the scan mouse from a full 3D orbit to the supplied vessel detail.

The camera moves through one full-resolution BP volume. The display window is
fixed throughout; zooming introduces no sharpening or intensity gain.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import subprocess
import time

import cv2
import h5py
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

ROOT = Path(__file__).resolve().parents[1]
FPS, DURATION, SIDE = 24, 24, 1080
CAP = 6.43388557434082
CROP = [70, 45, 590, 1010]
ROI = [233, 392, 89, 89]  # Matched to the user-supplied 520 x 965 frontal MIP.
SPACING = 0.1


def ease(x):
    x = np.clip(x, 0, 1)
    return x*x*x*(x*(x*6-15)+10)


def mix(a, b, t):
    return np.asarray(a)*(1-t) + np.asarray(b)*t


def prepare(source, cache):
    if cache.exists():
        return np.load(cache)
    with h5py.File(source) as f:
        x, y, z = (f[k + '_mm'][:] for k in 'xyz')
        slab = np.flatnonzero((z >= 1.9-1e-5) & (z <= 21.9+1e-5))
        volume = f['volume_yxz'][:, :, slab[0]:slab[-1]+1].transpose(2, 0, 1)
    h, w = volume.shape[1:]
    matrix = cv2.getRotationMatrix2D(((18-x[0])/.1, (-32-y[0])/.1), -2, 1)
    l, t, r, b = CROP
    volume = np.stack([
        cv2.warpAffine(plane, matrix, (w, h), flags=cv2.INTER_LINEAR)[h-b:h-t, l:r]
        for plane in volume
    ])
    np.save(cache, volume)
    return volume


def display_mask(volume, work_dir):
    """A conservative display envelope from the three orthogonal projections.

    Morphological operations change the display support only. Interior voxel
    intensities remain unfiltered; the source HDF5 is opened read-only.
    """
    x, y, width, height = ROI
    reference_detail = volume.max(0)[::-1][y:y+height, x:x+width].copy()
    masks = []
    for axis in range(3):
        mip = volume.max(axis)
        seed = ndi.gaussian_filter(mip, 2) > .8
        seed = cv2.morphologyEx(seed.astype('uint8'), cv2.MORPH_CLOSE,
                               cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (51, 51))).astype(bool)
        labels, count = ndi.label(seed)
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        largest = int(sizes.argmax())
        major = labels == largest
        near = ndi.distance_transform_edt(~major) < 50
        keep = [largest]
        for index in range(1, count+1):
            if index == largest or sizes[index] < 30:
                continue
            component = labels == index
            if not np.any(near[component]):
                continue
            # Keep the detached central tail signal. The isolated upper-right
            # boundary artifact lies outside the anatomical silhouette.
            if axis == 0:
                centre_x = np.nonzero(component)[1].mean()
                if not .2*mip.shape[1] < centre_x < .8*mip.shape[1]:
                    continue
            keep.append(index)
        seed = ndi.binary_fill_holes(np.isin(labels, keep))
        seed = cv2.dilate(seed.astype('uint8'),
                          cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))).astype(bool)
        masks.append(np.clip(ndi.distance_transform_edt(seed)/8, 0, 1).astype('float32'))
    xy, xz, yz = masks
    np.savez_compressed(work_dir/'display_masks.npz', xy=xy, xz=xz, yz=yz)
    volume *= xy[None, :, :]
    volume *= xz[:, None, :]
    volume *= yz[:, :, None]
    detail = volume.max(0)[::-1][y:y+height, x:x+width]
    audit = dict(target_mip_max_abs_change=float(np.abs(detail-reference_detail).max()),
                 target_mip_changed_pixels=int(np.count_nonzero(detail != reference_detail)))
    return volume, audit


def camera_state(seconds, centre, target, full_scale):
    seconds = min(seconds, DURATION)
    close_scale = math.exp(float(mix(math.log(15), math.log(4.45), ease(.2))))
    start_yaw, start_tilt = 28.4, -17.7
    yaw, tilt, focal, scale = start_yaw, start_tilt, centre, full_scale
    if seconds < 8.5:
        yaw += 360*ease((seconds-1)/7.5)
    elif seconds < 10.5:
        u = ease((seconds-8.5)/2)
        yaw, tilt = start_yaw*(1-u), start_tilt*(1-u)
    elif seconds < 11.2:
        yaw, tilt = 0, 0
    elif seconds < 15.2:
        u = ease((seconds-11.2)/4)
        yaw, tilt = 0, 0
        focal = mix(centre, target, u)
        scale = math.exp(float(mix(math.log(full_scale), math.log(15), u)))
    elif seconds < 16:
        # Limit the zoom to the previous film's 16-second field.
        u = ease(.2)*ease((seconds-15.2)/.6)
        yaw, tilt, focal = 0, 0, target
        scale = math.exp(float(mix(math.log(15), math.log(4.45), u)))
    elif seconds < 18:
        yaw, tilt, focal, scale = 0, 0, target, close_scale
    elif seconds < 22:
        u = ease((seconds-18)/4)
        yaw, tilt = 0, 0
        focal = mix(target, centre, u)
        scale = math.exp(float(mix(math.log(close_scale), math.log(full_scale), u)))
    else:
        u = ease((seconds-22)/2)
        yaw, tilt = start_yaw*u, start_tilt*u
    yaw, tilt = np.deg2rad([yaw, tilt])
    normal = np.array([np.sin(yaw)*np.cos(tilt), np.sin(tilt), np.cos(yaw)*np.cos(tilt)])
    up = np.array([0., -1., 0.])
    up -= np.dot(up, normal)*normal
    up /= np.linalg.norm(up)
    return focal, normal, up, scale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--work-dir', type=Path, required=True)
    ap.add_argument('--preview', action='store_true')
    args = ap.parse_args()
    args.work_dir.mkdir(parents=True, exist_ok=True)
    v = prepare(args.source, args.work_dir/'scan_sum_aligned_zyx.npy')
    v, mask_audit = display_mask(v, args.work_dir)
    size = SPACING*(np.array(v.shape[::-1])-1)
    centre = size/2
    target = np.array([(v.shape[2]-1-(ROI[0]+ROI[2]/2))*SPACING,
                       (ROI[1]+ROI[3]/2)*SPACING, centre[2]])
    full_scale = 56
    data = vtk.vtkImageData()
    data.SetDimensions(*v.shape[::-1])
    data.SetSpacing(SPACING, SPACING, SPACING)
    data.GetPointData().SetScalars(numpy_to_vtk(
        np.ascontiguousarray(v[::-1, ::-1, ::-1]).ravel(), deep=True, array_type=vtk.VTK_FLOAT))
    vmax = float(v.max())
    del v
    mapper = vtk.vtkGPUVolumeRayCastMapper()
    mapper.SetInputData(data)
    mapper.SetBlendModeToMaximumIntensity()
    mapper.AutoAdjustSampleDistancesOff()
    mapper.SetSampleDistance(.065)
    colors = vtk.vtkColorTransferFunction()
    colors.AddRGBPoint(0, 0, 0, 0)
    colors.AddRGBPoint(CAP, 1, 1, 1)
    opacity = vtk.vtkPiecewiseFunction()
    opacity.AddPoint(0, 1)
    opacity.AddPoint(vmax, 1)
    prop = vtk.vtkVolumeProperty()
    prop.SetColor(colors)
    prop.SetScalarOpacity(opacity)
    prop.SetInterpolationTypeToLinear()
    prop.ShadeOff()
    actor = vtk.vtkVolume()
    actor.SetMapper(mapper)
    actor.SetProperty(prop)
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0, 0, 0)
    renderer.AddVolume(actor)
    cam = renderer.GetActiveCamera()
    cam.ParallelProjectionOn()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetMultiSamples(0)
    win.SetSize(SIDE, SIDE)
    win.AddRenderer(renderer)
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(win)
    capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff()

    def frame(t):
        focal, normal, up, scale = camera_state(t, centre, target, full_scale)
        cam.SetFocalPoint(*focal)
        cam.SetPosition(*(focal+normal*500))
        cam.SetViewUp(*up)
        cam.SetParallelScale(scale)
        renderer.ResetCameraClippingRange()
        win.Render()
        capture.Modified()
        capture.Update()
        pixels = vtk_to_numpy(capture.GetOutput().GetPointData().GetScalars()).reshape(SIDE, SIDE, 3)
        return np.ascontiguousarray(pixels[::-1])

    key_times = [0, 3.5, 10.6, 16, 20, 24]
    sheet = Image.new('RGB', (1200, 850), '#10151b')
    draw = ImageDraw.Draw(sheet)
    for index, t in enumerate(key_times):
        start = time.monotonic()
        im = Image.fromarray(frame(t))
        im.save(args.work_dir/f'keyframe_{t:g}.png')
        sheet.paste(im.resize((400, 400)), ((index % 3)*400, (index//3)*425))
        draw.text(((index%3)*400+12, (index//3)*425+405), f'{t:g} seconds', fill='white')
        print(f'keyframe {t:g}s, render {time.monotonic()-start:.2f}s', flush=True)
    sheet.save(args.work_dir/'contact_sheet.png')
    if args.preview:
        win.Finalize()
        return
    movie = ROOT/'assets/media/overview-scan-detail.mp4'
    movie.parent.mkdir(parents=True, exist_ok=True)
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
               '-pix_fmt', 'rgb24', '-s', f'{SIDE}x{SIDE}', '-r', str(FPS), '-i', '-',
               '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
               '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(movie)]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE)
    start = time.monotonic()
    try:
        for index in range(FPS*DURATION):
            proc.stdin.write(frame(index/FPS).tobytes())
            if index % FPS == 0:
                print(f'FRAME {index}/{FPS*DURATION}, {time.monotonic()-start:.1f}s elapsed', flush=True)
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError('ffmpeg encoding failed')
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    finally:
        win.Finalize()
    poster = ROOT/'assets/images/showcase/overview-film-poster.webp'
    Image.open(args.work_dir/'keyframe_0.png').save(poster, quality=94, method=6)
    sha = hashlib.sha256()
    with args.source.open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            sha.update(chunk)
    record = dict(sample_id='20260114_192341_Scan1', source_name=args.source.name,
                  source_sha256=sha.hexdigest(), source='Equal-weight voxelwise BP sum: 1.44–5.76 MHz + 0.5–8 MHz',
                  display_shape_zyx=list(data.GetDimensions()[::-1]), voxel_spacing_mm=[.1, .1, .1],
                  xy_rotation_deg=2, rotation_centre_xy_mm=[18, -32], xy_crop_screen_pixels=CROP,
                  z_slab_mm=[1.9, 21.9], display_window=[0, CAP], gamma=1,
                  frangi_weight=0, fluence_gain=False,
                  display_mask=dict(method='Intersection of orthogonal foreground envelopes; presentation only',
                                    projection_gaussian_sigma_voxels=2, seed_threshold=.8,
                                    closing_ellipse_voxels=51, minimum_satellite_area_pixels=30,
                                    satellite_max_distance_mm=5, xy_satellite_centre_fraction=[.2,.8],
                                    dilation_ellipse_voxels=31, inward_feather_mm=.8,
                                    outside_value=0, original_source_modified=False, target_roi_audit=mask_audit),
                  render='3D maximum-intensity ray casting, linear interpolation, fixed display window',
                  ray_step_mm=.065, frame_size=[SIDE, SIDE], fps=FPS, duration_seconds=DURATION, bounding_box=False,
                  camera_projection='parallel', camera_full_parallel_scale_mm=full_scale,
                  camera_initial_yaw_tilt_deg=[28.4, -17.7], orbit_degrees=360,
                  focus_reference_roi_xywh_pixels=ROI,
                  closest_field_mm=2*camera_state(16, centre, target, full_scale)[3],
                  closest_view_from_previous_film_seconds=16, playback_end='Seamless return to opening camera',
                  reference_template_match_correlation=.9929325580596924,
                  sections=[dict(start=0, end=10.5, action='3D orbit and frontal alignment'),
                            dict(start=10.5, end=15.2, action='Whole specimen to central vascular field'),
                            dict(start=15.2, end=18, action='Settle at the previous 16-second vascular field and hold'),
                            dict(start=18, end=22, action='Smooth zoom out to the whole-body field'),
                            dict(start=22, end=24, action='Return to the opening 3D pose')],
                  movie='assets/media/overview-scan-detail.mp4', poster='assets/images/showcase/overview-film-poster.webp',
                  movie_sha256=hashlib.sha256(movie.read_bytes()).hexdigest(),
                  poster_sha256=hashlib.sha256(poster.read_bytes()).hexdigest())
    (ROOT/'data/overview-film.json').write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    provenance_file = ROOT/'data/display-provenance.json'
    provenance = json.loads(provenance_file.read_text(encoding='utf-8'))
    asset_names = {record['movie'], record['poster']}
    provenance['assets'] = [a for a in provenance['assets'] if a['file'] not in asset_names]
    for key in ['movie', 'poster']:
        provenance['assets'].append(dict(file=record[key], sha256=record[key+'_sha256'],
                                        source='scan_sum.h5', dimensions=[SIDE, SIDE],
                                        conversion='Full-resolution 3D camera render; fixed window; presentation envelope on black',
                                        settings='data/overview-film.json'))
    provenance_file.write_text(json.dumps(provenance, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(f'COMPLETE {movie} ({movie.stat().st_size} bytes)', flush=True)


if __name__ == '__main__':
    main()
