"""Compact browser MIPs: one linear uint8 calibration for an entire series."""
import gzip
import hashlib
import struct
import numpy as np


def encode_preview(pixels, valid):
    pixels = np.asarray(pixels, dtype='<f4')
    valid = np.ascontiguousarray(valid, dtype='u1')
    assert pixels.ndim == 3 and valid.shape == pixels.shape[1:]
    assert np.isfinite(pixels).all() and np.isin(valid, [0, 1]).all()
    offset = float(pixels.min())
    scale = (float(pixels.max()) - offset) / 255 or 1.0
    codes = np.rint((pixels.astype('f8') - offset) / scale).clip(0, 255).astype('u1')
    blob = struct.pack('<4sIIII2d', b'PAM2', *pixels.shape, 8, scale, offset)
    blob += codes.tobytes() + valid.tobytes()
    packed = gzip.compress(blob, compresslevel=6, mtime=0)
    metadata = dict(format='PAM2', encoding='gzip', dtype='uint8-linear',
                    shape_tyx=list(pixels.shape), bytes=len(packed), uncompressed_bytes=len(blob),
                    sha256=hashlib.sha256(packed).hexdigest(),
                    quantization=dict(bits=8, scale=scale, offset=offset,
                        calibration='one linear scale and offset shared by every timepoint',
                        maximum_pixel_absolute_error=scale / 2,
                        clipping=False, temporal_subsampling=False, spatial_subsampling=False))
    return packed, metadata


def decode_payload(packed):
    blob = gzip.decompress(packed)
    magic, n, h, w, flags = struct.unpack_from('<4sIIII', blob)
    if magic == b'PAM1' and flags == 1:
        offset = 20
        pixels = np.frombuffer(blob, dtype='<f4', count=n*h*w, offset=offset).reshape(n,h,w)
        offset += n*h*w*4
    elif magic == b'PAM2' and flags == 8:
        scale, zero = struct.unpack_from('<2d', blob, 20)
        pixels = np.frombuffer(blob, dtype='u1', count=n*h*w, offset=36).reshape(n,h,w).astype('f8')*scale+zero
        offset = 36+n*h*w
    else:
        raise ValueError('Unsupported MIP payload')
    assert len(blob) == offset+h*w
    valid = np.frombuffer(blob, dtype='u1', offset=offset).reshape(h,w).astype(bool)
    return pixels, valid
