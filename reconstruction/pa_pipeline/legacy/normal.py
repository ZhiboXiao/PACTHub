"""Prepare one published acquisition group from an already validated in-memory config."""
import copy
from .common import prepare_config
from .core.config import subset_frames
def prepare_normal(sample, *, frames=None):
    if not isinstance(sample,dict):
        raise TypeError('Use the public two-JSON loader before preparing RF')
    cfg=copy.deepcopy(sample)
    if frames is not None:cfg=subset_frames(cfg,list(frames))
    return prepare_config(cfg)
