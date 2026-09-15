# Modified by Infernux: NumPy-only type conversion, no framework/toolchain probing
# or terminal color dependencies.
import functools
import traceback
import warnings

import numpy as np
from .._lib import core as _ti_core
from .._logging import is_logging_effective
from . import impl
from ..types.primitive_types import (
    f16,
    f32,
    f64,
    i8,
    i16,
    i32,
    i64,
    u1,
    u8,
    u16,
    u32,
    u64,
)


def is_matrix_class(rhs):
    matrix_class = False
    try:
        if rhs._is_matrix_class:
            matrix_class = True
    except:
        pass
    return matrix_class


def is_taichi_class(rhs):
    taichi_class = False
    try:
        if rhs._is_taichi_class:
            taichi_class = True
    except:
        pass
    return taichi_class


def to_numpy_type(dt):
    """Convert taichi data type to its counterpart in numpy.

    Args:
        dt (DataType): The desired data type to convert.

    Returns:
        DataType: The counterpart data type in numpy.

    """
    if dt == f32:
        return np.float32
    if dt == f64:
        return np.float64
    if dt == i32:
        return np.int32
    if dt == i64:
        return np.int64
    if dt == i8:
        return np.int8
    if dt == i16:
        return np.int16
    if dt == u1:
        return np.bool_
    if dt == u8:
        return np.uint8
    if dt == u16:
        return np.uint16
    if dt == u32:
        return np.uint32
    if dt == u64:
        return np.uint64
    if dt == f16:
        return np.half
    assert False


def to_taichi_type(dt):
    """Convert NumPy data types to the compiler's numerical types.

    Args:
        dt (DataType): The desired data type to convert.

    Returns:
        DataType: The counterpart data type in taichi.

    """
    if type(dt) == _ti_core.DataType:
        return dt

    if dt == np.float32:
        return f32
    if dt == np.float64:
        return f64
    if dt == np.int32:
        return i32
    if dt == np.int64:
        return i64
    if dt == np.int8:
        return i8
    if dt == np.int16:
        return i16
    if dt == np.bool_:
        return u1
    if dt == np.uint8:
        return u8
    if dt == np.uint16:
        return u16
    if dt == np.uint32:
        return u32
    if dt == np.uint64:
        return u64
    if dt == np.half:
        return f16

    raise TypeError(f"Unsupported NumPy dtype: {dt}")


def cook_dtype(dtype):
    if isinstance(dtype, _ti_core.DataType):
        return dtype
    if isinstance(dtype, _ti_core.Type):
        return _ti_core.DataType(dtype)
    if dtype is float:
        return impl.get_runtime().default_fp
    if dtype is int:
        return impl.get_runtime().default_ip
    if dtype is bool:
        return u1
    raise ValueError(f"Invalid data type {dtype}")


def in_taichi_scope():
    return impl.inside_kernel()


def in_python_scope():
    return not in_taichi_scope()


def taichi_scope(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        assert in_taichi_scope(), f"{func.__name__} cannot be called in Python-scope"
        return func(*args, **kwargs)

    return wrapped


def python_scope(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        assert in_python_scope(), f"{func.__name__} cannot be called in Taichi-scope"
        return func(*args, **kwargs)

    return wrapped


def warning(msg, warning_type=UserWarning, stacklevel=1, print_stack=True):
    """Print a warning message. Note that the builtin `warnings` module is
    unreliable since it may be suppressed by other packages such as IPython.

    Args:
        msg (str): message to print.
        warning_type (Type[Warning]): type of warning.
        stacklevel (int): warning stack level from the caller.
        print_stack (bool): whether to print the stack
    """
    if not is_logging_effective("warn"):
        return
    if print_stack:
        msg += f"\n{get_traceback(stacklevel)}"
    warnings.warn(msg, warning_type)


def get_traceback(stacklevel=1):
    s = traceback.extract_stack()[: -1 - stacklevel]
    return "".join(traceback.format_list(s))


__all__ = []
