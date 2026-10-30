"""Universal back-projection derived from Xu & Wang, Phys Rev E 71 (2005).

Algorithm source: https://doi.org/10.1103/PhysRevE.71.016706, Eqs. (20)-(22).
    b_i(t) = 2 * (p_i(t) - t * dp_i(t)/dt)
    Omega_i(x) = area_i * n_i dot (x - detector_i) / |x - detector_i|**3
    p0(x) = sum_i Omega_i(x) * b_i(|x-detector_i|/c) / sum_i Omega_i(x)

Numerical choices made here: second-order finite differences, linear temporal
interpolation, equal surface-cell areas by default, signed float32 output.
This module accepts physical time axes; it has no dataset-specific clock,
frame-selection, angular aperture, apodization or display processing.
Normals point inward. Use reconstruction points on the inward side of the
measurement surface. Finite/partial coverage is an approximate reconstruction.
"""
import numpy as np

DOI = '10.1103/PhysRevE.71.016706'
IMPLEMENTATION = 'xu_wang_2005_ubp_v1'


def temporal_term(pressure_ct, time_s):
    """Sample Eq. (20)'s back-projection term; retain its signed values."""
    if np.iscomplexobj(pressure_ct):
        raise ValueError('UBP expects real signed pressure, not an analytic/envelope signal')
    pressure = np.asarray(pressure_ct, dtype=np.float64)
    t = np.asarray(time_s, dtype=np.float64)
    if pressure.ndim != 2 or t.ndim != 1 or pressure.shape[1] != len(t) or len(t) < 3:
        raise ValueError('Expected real pressure [detector,time] and at least 3 time samples')
    if not np.isfinite(pressure).all() or not np.isfinite(t).all():
        raise ValueError('Pressure and physical times must be finite')
    dt = np.diff(t)
    if np.any(dt <= 0) or not np.allclose(dt, dt[0], rtol=1e-7, atol=0):
        raise ValueError('Physical time samples must be increasing and uniformly spaced')
    derivative = np.gradient(pressure, float(dt[0]), axis=1, edge_order=2)
    return np.asarray(2.0 * (pressure - t[None, :] * derivative), dtype=np.float32)


class UBPProjector:
    """Prepare pressure once, then evaluate any points in physical coordinates."""
    def __init__(self, pressure_ct, time_s, detector_xyz_mm, normals_xyz, *,
                 sound_speed_m_s, surface_areas=None, backend='cpu'):
        self.c_mm_s = 1000.0 * float(sound_speed_m_s)
        if not np.isfinite(self.c_mm_s) or self.c_mm_s <= 0:
            raise ValueError('Sound speed must be finite and positive')
        t = np.asarray(time_s, dtype=np.float64)
        bp_signal = temporal_term(pressure_ct, t)
        detector = np.asarray(detector_xyz_mm, dtype=np.float64)
        normal = np.asarray(normals_xyz, dtype=np.float64)
        n = len(bp_signal)
        if n == 0 or detector.shape != (n, 3) or normal.shape != (n, 3):
            raise ValueError('One detector and inward normal are required per pressure trace')
        if not np.isfinite(detector).all() or not np.isfinite(normal).all():
            raise ValueError('Detector geometry must be finite')
        if not np.allclose(np.linalg.norm(normal, axis=1), 1.0, rtol=1e-6, atol=1e-6):
            raise ValueError('Supply unit inward normals')
        area = np.ones(n, dtype=np.float64) if surface_areas is None else np.asarray(surface_areas, dtype=np.float64)
        if area.shape != (n,) or not np.isfinite(area).all() or np.any(area <= 0):
            raise ValueError('Surface quadrature areas must be positive and match detector count')
        if backend == 'cpu':
            xp = np
        elif backend == 'cuda':
            import cupy as xp
            if xp.cuda.runtime.getDeviceCount() < 1:
                raise RuntimeError('An NVIDIA GPU is required for backend=cuda')
        else:
            raise ValueError('backend must be cpu or cuda')
        self.xp = xp
        self.signal = xp.asarray(bp_signal)
        self.detector = xp.asarray(detector)
        self.normal = xp.asarray(normal)
        self.area = xp.asarray(area)
        self.t0 = float(t[0])
        self.dt = float(t[1] - t[0])

    def evaluate(self, points_xyz_mm, *, detector_batch=256):
        """Evaluate Eqs. (21)-(22). Out-of-record signals are zero extended.

        The denominator is geometric coverage, including detector directions
        whose arrival falls outside the recording. No invalid-time renormalization.
        """
        if type(detector_batch) is not int or detector_batch < 1:
            raise ValueError('detector_batch must be a positive integer')
        points = np.asarray(points_xyz_mm, dtype=np.float64)
        if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
            raise ValueError('Supply finite [point,3] coordinates in mm')
        xp = self.xp
        xyz = xp.asarray(points)
        total = xp.zeros(len(points), dtype=xp.float64)
        coverage = xp.zeros(len(points), dtype=xp.float64)
        nt = self.signal.shape[1]
        for start in range(0, len(self.detector), detector_batch):
            stop = min(start + detector_batch, len(self.detector))
            ds = self.detector[start:stop]
            ns = self.normal[start:stop]
            dx = xyz[None, :, 0] - ds[:, None, 0]
            dy = xyz[None, :, 1] - ds[:, None, 1]
            dz = xyz[None, :, 2] - ds[:, None, 2]
            distance_sq = dx * dx + dy * dy + dz * dz
            radius = xp.sqrt(distance_sq)
            dot = dx * ns[:, None, 0] + dy * ns[:, None, 1] + dz * ns[:, None, 2]
            # Eq. (22); no detector-response weighting or angular window.
            denominator = xp.where(radius > 0, distance_sq * radius, 1.0)
            omega = self.area[start:stop, None] * xp.maximum(dot, 0) / denominator
            coverage += omega.sum(axis=0, dtype=xp.float64)
            fractional_index = (radius / self.c_mm_s - self.t0) / self.dt
            valid = (fractional_index >= 0) & (fractional_index <= nt - 1)
            lower = xp.clip(xp.floor(fractional_index), 0, nt - 2).astype(xp.int64)
            fraction = xp.clip(fractional_index - lower, 0, 1)
            channel = xp.arange(stop-start)[:, None]
            signals = self.signal[start:stop]
            value = (1-fraction) * signals[channel, lower] + fraction * signals[channel, lower+1]
            total += xp.sum(omega * xp.where(valid, value, 0), axis=0, dtype=xp.float64)
        signed = total / xp.where(coverage > 0, coverage, 1)
        answer = signed.astype(xp.float32)
        return np.asarray(answer) if xp is np else xp.asnumpy(answer)


def ubp_points(pressure_ct, time_s, detector_xyz_mm, normals_xyz, points_xyz_mm, *,
               sound_speed_m_s, surface_areas=None, backend='cpu',
               point_batch=8192, detector_batch=256):
    """Reconstruct arbitrary locations; coordinates mm, time s, speed m/s."""
    if type(point_batch) is not int or point_batch < 1:
        raise ValueError('point_batch must be a positive integer')
    points = np.asarray(points_xyz_mm)
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError('Expected [point,3] coordinates')
    engine = UBPProjector(pressure_ct, time_s, detector_xyz_mm, normals_xyz,
                          sound_speed_m_s=sound_speed_m_s, surface_areas=surface_areas, backend=backend)
    result = np.empty(len(points), dtype=np.float32)
    for first in range(0, len(points), point_batch):
        result[first:first+point_batch] = engine.evaluate(points[first:first+point_batch], detector_batch=detector_batch)
    return result


def ubp_volume(pressure_ct, time_s, detector_xyz_mm, normals_xyz, axes_xyz_mm, *,
               sound_speed_m_s, surface_areas=None, backend='cpu',
               point_batch=8192, detector_batch=256, progress=None):
    """Return the signed linear volume [z,y,x], with no image postprocessing."""
    if type(point_batch) is not int or point_batch < 1:
        raise ValueError('point_batch must be a positive integer')
    axes = [np.asarray(a, dtype=np.float64) for a in axes_xyz_mm]
    if len(axes) != 3 or any(a.ndim != 1 or len(a) == 0 or not np.isfinite(a).all() for a in axes):
        raise ValueError('Supply three finite nonempty physical coordinate axes')
    nx, ny, nz = map(len, axes)
    engine = UBPProjector(pressure_ct, time_s, detector_xyz_mm, normals_xyz,
                          sound_speed_m_s=sound_speed_m_s, surface_areas=surface_areas, backend=backend)
    flat = np.empty(nx*ny*nz, dtype=np.float32)
    for start in range(0, len(flat), point_batch):
        ids = np.arange(start, min(start+point_batch, len(flat)))
        coordinates = np.column_stack((axes[0][ids % nx], axes[1][(ids//nx) % ny], axes[2][ids//(nx*ny)]))
        flat[ids] = engine.evaluate(coordinates, detector_batch=detector_batch)
        if progress is not None:
            progress(int(ids[-1])+1, len(flat))
    return flat.reshape(nz, ny, nx)


def implementation_record(backend):
    return dict(implementation=IMPLEMENTATION, source_doi=DOI, source_equations=[20,21,22],
                algorithm='universal_backprojection', pressure_term='2*(p-t*dp_dt)',
                derivative='second_order_finite_difference', time_interpolation='linear',
                quadrature='equal_area_surface_cells', normalization='sum_geometric_solid_angles',
                output='signed_float32', geometry_and_accumulation='float64',
                array_backend=backend, out_of_record_signal='zero', custom_cuda_extension=False)
