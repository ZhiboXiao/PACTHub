"""Linear sensor preprocessing; historical defaults remain opt-in."""
from __future__ import annotations

import numpy as np
import torch


def masked_channel_demean(values: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """C_M on [time,channel], including zero-support channels (C_M=0)."""
    masked = values * mask
    count = mask.sum(dim=0, keepdim=True).clamp_min(1)
    mean = masked.sum(dim=0, keepdim=True) / count
    return (masked - mean) * mask


def zero_dc_bandpass(kernel: np.ndarray) -> np.ndarray:
    """Correct the existing FIR, then retain its numerical FFT-peak convention."""
    kernel = np.asarray(kernel, dtype=np.float64).reshape(-1).copy()
    kernel -= kernel.mean()
    kernel /= np.max(np.abs(np.fft.fft(kernel, 4096)))
    result = kernel.astype(np.float32)
    if abs(result.sum(dtype=np.float64)) >= 1e-7:
        raise ValueError('zero-DC FIR exceeds float32 rounding tolerance')
    return result
