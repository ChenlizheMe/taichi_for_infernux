# Modified by Infernux in 2026: private compiler-relative imports.
import functools

from .._lib import core as _ti_core
from .._logging import info

# Infernux owns diagnostics and does not carry Taichi's process-global Python
# print buffer. Kernel print is outside the engine compute authoring surface.
pybuf_enabled = False


def _shell_pop_print(old_call):
    if not pybuf_enabled:
        # zero-overhead!
        return old_call

    info("Graphical python shell detected, using wrapped sys.stdout")

    @functools.wraps(old_call)
    def new_call(*args, **kwargs):
        ret = old_call(*args, **kwargs)
        # print's in kernel won't take effect until ti.sync(), discussion:
        # https://github.com/taichi-dev/taichi/pull/1303#discussion_r444897102
        print(_ti_core.pop_python_print_buffer(), end="")
        return ret

    return new_call
