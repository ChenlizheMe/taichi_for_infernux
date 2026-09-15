# Modified by Infernux in 2026: private compiler-relative imports.
"""Minimal type surface retained for the Infernux Vulkan compiler frontend.

The fork no longer publishes Taichi's quantized, texture or container author
API from this package. External-array annotations are a temporary private IR
bridge for ``inx.buffer`` and are constructed only by Infernux.
"""

from . import annotations, buffer_type, primitive_types
from .annotations import template
from .buffer_type import BufferType, BufferTypeMetadata, external_buffer
from .compound_types import CompoundType, matrix, vector
from .primitive_types import *

__all__ = [
    "CompoundType",
    "BufferType",
    "BufferTypeMetadata",
    "matrix",
    "external_buffer",
    "template",
    "vector",
]
