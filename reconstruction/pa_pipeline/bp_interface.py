"""BP dispatch: public Xu-Wang UBP by default, with optional local override."""
from .backends.bp_adapter import reconstruct as public_reconstruct, public_profile

_implementation = public_reconstruct


def set_bp_backend(function):
    """Register a local callable with the documented reconstruct signature."""
    global _implementation
    if function is not None and not callable(function):
        raise TypeError('BP backend must be callable or None')
    _implementation = function


def bp_available():
    return _implementation is not None


def require_bp_backend():
    if not bp_available():
        raise RuntimeError('BP backend is disabled. Register an implementation '
                           'with pa_pipeline.bp_interface.set_bp_backend before BP, '
                           'automatic FOV or sound-speed selection. See BP_INTERFACE.md.')


def reconstruct(data, sensors, cfg, backend='cuda', speed=None,
                volume_sink=None, normals=None):
    require_bp_backend()
    return _implementation(data, sensors, cfg, backend=backend, speed=speed,
                           volume_sink=volume_sink, normals=normals)


def prepare_bp_profile(cfg):
    """Record the public baseline options before validation and preprocessing."""
    return public_profile(cfg) if _implementation is public_reconstruct else cfg
