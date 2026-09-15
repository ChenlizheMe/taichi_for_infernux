# Modified by Infernux in 2026: private compiler-relative imports.
"""Compiler annotation for an engine-owned external buffer.

This is metadata only.  It never allocates memory and is created solely by
the private Infernux frontend from an ``inx.buffer`` description.
"""

from ..lang.enums import Layout, to_boundary_enum
from ..lang import util
from .compound_types import CompoundType, matrix, vector


class BufferTypeMetadata:
    def __init__(self, element_type, shape=None, needs_grad=False):
        self.element_type = element_type
        self.shape = shape
        self.layout = Layout.AOS
        self.needs_grad = needs_grad


def _matrix_dtype(element_dim, element_shape, primitive_dtype):
    if isinstance(primitive_dtype, CompoundType):
        raise TypeError("dtype and element shape cannot both describe a compound type")
    if element_dim == 0 or (element_shape is not None and len(element_shape) == 0):
        return primitive_dtype
    if element_dim is not None:
        if element_dim < 0 or element_dim > 2:
            raise ValueError("buffer elements may only be scalars, vectors, or matrices")
        if element_shape is not None and len(element_shape) != element_dim:
            raise ValueError("element_shape does not match element_dim")
        return vector(None, primitive_dtype) if element_dim == 1 else matrix(None, None, primitive_dtype)
    if element_shape is not None:
        if len(element_shape) > 2:
            raise ValueError("buffer elements may only be scalars, vectors, or matrices")
        return (
            vector(element_shape[0], primitive_dtype)
            if len(element_shape) == 1
            else matrix(element_shape[0], element_shape[1], primitive_dtype)
        )
    return None


class BufferType:
    def __init__(
        self,
        dtype=None,
        ndim=None,
        element_dim=None,
        element_shape=None,
        needs_grad=None,
        boundary="unsafe",
    ):
        self.dtype = (
            _matrix_dtype(element_dim, element_shape, dtype)
            if element_dim is not None or element_shape is not None
            else dtype
        )
        self.ndim = ndim
        self.layout = Layout.AOS
        self.needs_grad = needs_grad
        self.boundary = to_boundary_enum(boundary)

    def check_matched(self, actual: BufferTypeMetadata, arg_name: str):
        if isinstance(self.dtype, CompoundType):
            if not self.dtype.check_matched(actual.element_type):
                raise ValueError(f"buffer argument {arg_name} has an incompatible element type")
        elif self.dtype is not None and util.cook_dtype(self.dtype) != actual.element_type:
            raise TypeError(f"buffer argument {arg_name} has an incompatible element type")
        if self.ndim is not None and actual.shape is not None and self.ndim != len(actual.shape):
            raise ValueError(f"buffer argument {arg_name} has an incompatible rank")
        if self.needs_grad is not None and self.needs_grad > actual.needs_grad:
            raise ValueError(f"buffer argument {arg_name} has incompatible gradient metadata")

    def __repr__(self):
        return f"BufferType(dtype={self.dtype}, ndim={self.ndim}, layout={self.layout})"


external_buffer = BufferType

__all__ = ["BufferType", "BufferTypeMetadata", "external_buffer"]
