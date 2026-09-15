# Modified by the Infernux project in 2026 for the private compiler frontend.
#
# This package is an implementation detail of ``Infernux.compute``.  Import the
# exact compiler surface instead of publishing Taichi's author/runtime API via
# ``taichi.lang import *``.  The remaining lang modules are being separated
# from field/SNode/ndarray ownership incrementally; they must not become a
# second public compute API in the meantime.
from ._lib import core as _ti_core
from . import lang
from .lang import impl
from .lang.kernel_impl import kernel
from . import types
from .types.primitive_types import f32, i32, u32

vulkan = _ti_core.vulkan


def __getattr__(attr):
    if attr == "cfg":
        return None if lang.impl.get_runtime().prog is None else lang.impl.current_cfg()
    raise AttributeError(f"module '{__name__}' has no attribute '{attr}'")


__version__ = (
    _ti_core.get_version_major(),
    _ti_core.get_version_minor(),
    _ti_core.get_version_patch(),
)

__all__ = ["f32", "i32", "kernel", "lang", "types", "u32", "vulkan"]
