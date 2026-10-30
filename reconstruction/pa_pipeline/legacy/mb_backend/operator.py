"""Numeric definitions extracted unchanged from the reviewed V3 implementation."""
import math
import numpy as np
import torch
from .matched_temporal import masked_channel_demean

def temporal_convolution(
    values: torch.Tensor,
    kernel: torch.Tensor,
    zero_index: int,
    transpose: bool,
) -> torch.Tensor:
    if transpose:
        kernel = torch.flip(kernel, dims=(0,))
        zero_index = kernel.numel() - zero_index + 1
    num_times = values.shape[0]
    if not 1 <= zero_index <= kernel.numel():
        raise ValueError("temporal origin must be one-based within the kernel")
    full_length = num_times + kernel.numel() - 1
    fft_length = 1 << int(math.ceil(math.log2(full_length)))
    values_spectrum = torch.fft.fft(values, n=fft_length, dim=0)
    kernel_spectrum = torch.fft.fft(kernel, n=fft_length).reshape(-1, 1)
    full = torch.fft.ifft(values_spectrum * kernel_spectrum, dim=0).real
    start = zero_index - 1
    return full[start : start + num_times, :].contiguous()

class ExactV3Operator:
    def __init__(
        self,
        projector,
        inputs: dict,
        spatial_model: str = "quadrature",
        sensor_batch_size: int | None = None,
        dual_speed: dict | None = None,
    ):
        if spatial_model not in {"quadrature", "analytic_disk"}:
            raise ValueError(
                "spatial_model must be 'quadrature' or 'analytic_disk'"
            )
        self.projector = projector
        self.inputs = inputs
        self.channel_response = None
        self.spatial_model = spatial_model
        self.dual_speed = dual_speed
        if dual_speed is not None and spatial_model != "quadrature":
            raise ValueError(
                "planar dual speed requires numerical receiver quadrature; "
                "the homogeneous analytic-disk formula is not valid across "
                "a material interface"
            )
        if dual_speed is not None:
            required = {
                "speed1_mps",
                "speed2_mps",
                "plane_point_mm",
                "plane_normal_region1",
            }
            missing = sorted(required.difference(dual_speed))
            if missing:
                raise ValueError(f"dual-speed parameters missing {missing}")
        self.nx, self.ny, self.nz = [int(v) for v in inputs["grid_size"]]
        self.x0, self.y0, self.z0 = [float(v) for v in inputs["grid_origin"]]
        self.dx, self.dy, self.dz = [float(v) for v in inputs["grid_spacing"]]

        num_sensors = int(inputs["sensors"].shape[1])
        if sensor_batch_size is None:
            # Joint rotational acquisitions are concatenated receiver blocks.
            # Keeping each CUDA kernel at the native 1024-element size avoids
            # host long-kernel termination.  This is the exact identity
            # A.T b = sum_i A_i.T b_i, not an approximation.
            sensor_batch_size = 1024 if num_sensors > 1024 else num_sensors
        if sensor_batch_size < 1:
            raise ValueError("sensor_batch_size must be positive")
        self.sensor_batch_size = min(int(sensor_batch_size), num_sensors)
        self.num_sensor_batches = (
            num_sensors + self.sensor_batch_size - 1
        ) // self.sensor_batch_size

    def _dual_speed_arguments(self) -> tuple[float, ...]:
        if self.dual_speed is None:
            raise RuntimeError("dual-speed arguments requested in single-speed mode")
        point = np.asarray(
            self.dual_speed["plane_point_mm"], dtype=np.float64
        ).reshape(3)
        normal = np.asarray(
            self.dual_speed["plane_normal_region1"], dtype=np.float64
        ).reshape(3)
        return (
            float(self.dual_speed["speed1_mps"]),
            float(self.dual_speed["speed2_mps"]),
            float(point[0]),
            float(point[1]),
            float(point[2]),
            float(normal[0]),
            float(normal[1]),
            float(normal[2]),
        )

    def _sensor_slices(self):
        num_sensors = int(self.inputs["sensors"].shape[1])
        for first in range(0, num_sensors, self.sensor_batch_size):
            yield slice(first, min(first + self.sensor_batch_size, num_sensors))

    def _project_sensor_support(self, values: torch.Tensor) -> torch.Tensor:
        if self.inputs.get("matched_channel_demean", False):
            return masked_channel_demean(values, self.inputs["data_mask_gpu"])
        return values * self.inputs["data_mask_gpu"]

    def _forward_sensor_chain(self, physical: torch.Tensor) -> torch.Tensor:
        if self.channel_response is not None:
            physical = self.channel_response.physical_forward(physical)
        filtered = temporal_convolution(physical, self.inputs["kernel_gpu"],
                                        self.inputs["zero_index"], False)
        return self._project_sensor_support(filtered)

    def forward(self, volume_zyx: torch.Tensor) -> torch.Tensor:
        if self.spatial_model == "analytic_disk":
            physical = torch.empty(
                (
                    self.inputs["num_samples"],
                    self.inputs["sensors"].shape[1],
                ),
                dtype=volume_zyx.dtype,
                device=volume_zyx.device,
            )
            for sensor_slice in self._sensor_slices():
                physical[:, sensor_slice] = self.projector.analytic_forward(
                    volume_zyx,
                    self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                    self.inputs["sensor_radius_mm"],
                    self.inputs["num_samples"],
                    self.inputs["fs_mhz"],
                    self.inputs["predelay_samples"],
                    self.inputs["sound_speed_mps"],
                    self.x0,
                    self.y0,
                    self.z0,
                    self.dx,
                    self.dy,
                    self.dz,
                )
        else:
            physical = torch.empty(
                (
                    self.inputs["num_samples"],
                    self.inputs["sensors"].shape[1],
                ),
                dtype=volume_zyx.dtype,
                device=volume_zyx.device,
            )
            for sensor_slice in self._sensor_slices():
                common = (
                    volume_zyx,
                    self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                    self.inputs["offsets_gpu"][:, :, sensor_slice].contiguous(),
                    self.inputs["weights_gpu"],
                    self.inputs["num_samples"],
                    self.inputs["fs_mhz"],
                    self.inputs["predelay_samples"],
                )
                if self.dual_speed is None:
                    physical[:, sensor_slice] = self.projector.forward(
                        *common,
                        self.inputs["sound_speed_mps"],
                        self.x0,
                        self.y0,
                        self.z0,
                        self.dx,
                        self.dy,
                        self.dz,
                    )
                else:
                    physical[:, sensor_slice] = self.projector.dual_speed_forward(
                        *common,
                        *self._dual_speed_arguments(),
                        self.x0,
                        self.y0,
                        self.z0,
                        self.dx,
                        self.dy,
                        self.dz,
                    )
        return self._forward_sensor_chain(physical)

    def adjoint(self, sensor_data: torch.Tensor) -> torch.Tensor:
        masked = self._project_sensor_support(sensor_data)
        physical = temporal_convolution(
            masked,
            self.inputs["kernel_gpu"],
            self.inputs["zero_index"],
            True,
        )
        if self.channel_response is not None:
            physical = self.channel_response.physical_adjoint(physical)
        if self.spatial_model == "analytic_disk":
            output = torch.zeros(
                (self.nz, self.ny, self.nx),
                dtype=sensor_data.dtype,
                device=sensor_data.device,
            )
            for sensor_slice in self._sensor_slices():
                output.add_(
                    self.projector.analytic_adjoint(
                        physical[:, sensor_slice].contiguous(),
                        self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                        self.inputs["sensor_radius_mm"],
                        self.nx,
                        self.ny,
                        self.nz,
                        self.inputs["fs_mhz"],
                        self.inputs["predelay_samples"],
                        self.inputs["sound_speed_mps"],
                        self.x0,
                        self.y0,
                        self.z0,
                        self.dx,
                        self.dy,
                        self.dz,
                    )
                )
            return output
        output = torch.zeros(
            (self.nz, self.ny, self.nx),
            dtype=sensor_data.dtype,
            device=sensor_data.device,
        )
        for sensor_slice in self._sensor_slices():
            common = (
                physical[:, sensor_slice].contiguous(),
                self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                self.inputs["offsets_gpu"][:, :, sensor_slice].contiguous(),
                self.inputs["weights_gpu"],
                self.nx,
                self.ny,
                self.nz,
                self.inputs["fs_mhz"],
                self.inputs["predelay_samples"],
            )
            if self.dual_speed is None:
                batch_output = self.projector.adjoint(
                    *common,
                    self.inputs["sound_speed_mps"],
                    self.x0,
                    self.y0,
                    self.z0,
                    self.dx,
                    self.dy,
                    self.dz,
                )
            else:
                batch_output = self.projector.dual_speed_adjoint(
                    *common,
                    *self._dual_speed_arguments(),
                    self.x0,
                    self.y0,
                    self.z0,
                    self.dx,
                    self.dy,
                    self.dz,
                )
            output.add_(batch_output)
        return output

    def sparse_forward(
        self,
        source_positions: torch.Tensor,
        source_amplitudes: torch.Tensor,
    ) -> torch.Tensor:
        """Apply the identical V3 physics to fixed off/dense-grid sources.

        ``source_positions`` has shape ``[3,K]`` in millimetres. A source
        placed exactly at a voxel centre is physically identical to that
        voxel in :meth:`forward`; only the computational representation is
        sparse.
        """

        if self.dual_speed is not None:
            raise NotImplementedError(
                "sparse-source execution is not yet enabled for dual speed; "
                "use the exact dense forward and full-grid adjoint"
            )

        if self.spatial_model == "analytic_disk":
            physical = torch.empty(
                (
                    self.inputs["num_samples"],
                    self.inputs["sensors"].shape[1],
                ),
                dtype=source_amplitudes.dtype,
                device=source_amplitudes.device,
            )
            for sensor_slice in self._sensor_slices():
                physical[:, sensor_slice] = (
                    self.projector.analytic_sparse_forward(
                        source_positions.contiguous(),
                        source_amplitudes.contiguous(),
                        self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                        self.inputs["sensor_radius_mm"],
                        self.inputs["num_samples"],
                        self.inputs["fs_mhz"],
                        self.inputs["predelay_samples"],
                        self.inputs["sound_speed_mps"],
                    )
                )
        else:
            physical = torch.empty(
                (
                    self.inputs["num_samples"],
                    self.inputs["sensors"].shape[1],
                ),
                dtype=source_amplitudes.dtype,
                device=source_amplitudes.device,
            )
            for sensor_slice in self._sensor_slices():
                physical[:, sensor_slice] = self.projector.sparse_forward(
                    source_positions.contiguous(),
                    source_amplitudes.contiguous(),
                    self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                    self.inputs["offsets_gpu"][:, :, sensor_slice].contiguous(),
                    self.inputs["weights_gpu"],
                    self.inputs["num_samples"],
                    self.inputs["fs_mhz"],
                    self.inputs["predelay_samples"],
                    self.inputs["sound_speed_mps"],
                )
        return self._forward_sensor_chain(physical)

    def active_exact_forward(
        self,
        volume_zyx: torch.Tensor,
        dense_fraction_threshold: float = 0.6,
    ) -> tuple[torch.Tensor, dict]:
        """Use every strict nonzero voxel, with no top-K approximation.

        The sparse and dense projectors implement the same geometry.  This
        method changes only the execution representation: all nonzero
        amplitudes are retained, while exact zeros are omitted from the
        forward launch because their contribution is identically zero.
        The caller must continue to use the full-grid adjoint so omitted
        zero voxels can reactivate on the next update.
        """

        if not 0.0 < dense_fraction_threshold <= 1.0:
            raise ValueError("dense_fraction_threshold must be in (0,1]")
        if self.dual_speed is not None:
            # Correctness-preserving fallback.  It retains every voxel and
            # avoids silently calling the homogeneous sparse projector.
            return self.forward(volume_zyx), {
                "backend": "dense_dual_speed",
                "active_count": int(torch.count_nonzero(volume_zyx).item()),
                "active_fraction": float(torch.count_nonzero(volume_zyx).item())
                / volume_zyx.numel(),
            }
        flat = volume_zyx.reshape(-1)
        active_indices = torch.nonzero(flat, as_tuple=False).reshape(-1)
        active_count = active_indices.numel()
        active_fraction = active_count / flat.numel()
        if active_fraction >= dense_fraction_threshold:
            return self.forward(volume_zyx), {
                "backend": "dense",
                "active_count": active_count,
                "active_fraction": active_fraction,
            }

        if active_count == 0:
            prediction = torch.zeros(
                (self.inputs["num_samples"], self.inputs["sensors"].shape[1]),
                dtype=volume_zyx.dtype,
                device=volume_zyx.device,
            )
            return prediction, {
                "backend": "sparse_all_nonzero",
                "active_count": 0,
                "active_fraction": 0.0,
            }

        plane = self.nx * self.ny
        iz = torch.div(active_indices, plane, rounding_mode="floor")
        remainder = active_indices - iz * plane
        iy = torch.div(remainder, self.nx, rounding_mode="floor")
        ix = remainder - iy * self.nx
        positions = torch.stack(
            (
                self.x0 + self.dx * ix,
                self.y0 + self.dy * iy,
                self.z0 + self.dz * iz,
            )
        ).to(dtype=torch.float32).contiguous()
        amplitudes = flat[active_indices].contiguous()
        prediction = self.sparse_forward(positions, amplitudes)
        return prediction, {
            "backend": "sparse_all_nonzero",
            "active_count": active_count,
            "active_fraction": active_fraction,
        }

    def sparse_adjoint(
        self,
        sensor_data: torch.Tensor,
        source_positions: torch.Tensor,
    ) -> torch.Tensor:
        """Return the matched gradient for sparse source amplitudes."""

        if self.dual_speed is not None:
            raise NotImplementedError(
                "sparse-source amplitude adjoint is not yet enabled for dual speed"
            )

        masked = sensor_data * self.inputs["data_mask_gpu"]
        physical = temporal_convolution(
            masked,
            self.inputs["kernel_gpu"],
            self.inputs["zero_index"],
            True,
        )
        if self.spatial_model == "analytic_disk":
            output = torch.zeros(
                source_positions.shape[1],
                dtype=sensor_data.dtype,
                device=sensor_data.device,
            )
            for sensor_slice in self._sensor_slices():
                output.add_(
                    self.projector.analytic_sparse_adjoint(
                        physical[:, sensor_slice].contiguous(),
                        source_positions.contiguous(),
                        self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                        self.inputs["sensor_radius_mm"],
                        self.inputs["fs_mhz"],
                        self.inputs["predelay_samples"],
                        self.inputs["sound_speed_mps"],
                    )
                )
            return output
        output = torch.zeros(
            source_positions.shape[1],
            dtype=sensor_data.dtype,
            device=sensor_data.device,
        )
        for sensor_slice in self._sensor_slices():
            output.add_(
                self.projector.sparse_adjoint(
                    physical[:, sensor_slice].contiguous(),
                    source_positions.contiguous(),
                    self.inputs["sensors_gpu"][:, sensor_slice].contiguous(),
                    self.inputs["offsets_gpu"][:, :, sensor_slice].contiguous(),
                    self.inputs["weights_gpu"],
                    self.inputs["fs_mhz"],
                    self.inputs["predelay_samples"],
                    self.inputs["sound_speed_mps"],
                )
            )
        return output

def squared_norm(value: torch.Tensor) -> torch.Tensor:
    return torch.sum(value * value)

def norm_value(value: torch.Tensor) -> float:
    return float(torch.sqrt(squared_norm(value)).item())

def tv_gradient(volume: torch.Tensor):
    gx = torch.zeros_like(volume)
    gy = torch.zeros_like(volume)
    gz = torch.zeros_like(volume)
    gx[:, :, :-1] = volume[:, :, 1:] - volume[:, :, :-1]
    gy[:, :-1, :] = volume[:, 1:, :] - volume[:, :-1, :]
    gz[:-1, :, :] = volume[1:, :, :] - volume[:-1, :, :]
    return gx, gy, gz

def tv_adjoint(px: torch.Tensor, py: torch.Tensor, pz: torch.Tensor):
    result = torch.zeros_like(px)
    result[:, :, 0] -= px[:, :, 0]
    result[:, :, 1:-1] += px[:, :, :-2] - px[:, :, 1:-1]
    result[:, :, -1] += px[:, :, -2]
    result[:, 0, :] -= py[:, 0, :]
    result[:, 1:-1, :] += py[:, :-2, :] - py[:, 1:-1, :]
    result[:, -1, :] += py[:, -2, :]
    result[0, :, :] -= pz[0, :, :]
    result[1:-1, :, :] += pz[:-2, :, :] - pz[1:-1, :, :]
    result[-1, :, :] += pz[-2, :, :]
    return result
