# Modified by Infernux in 2026: private compiler-relative imports.
"""Native compiler loading inside the Infernux wheel.

Modified from upstream Taichi: use the packaged native module directly.
No global PATH/dlopen changes, wheel-repair advice, timestamp probing or
import-time banner. Infernux owns device initialization and execution.
"""

import os
import sys


def in_docker():
    return bool(os.environ.get("TI_IN_DOCKER", ""))


def get_os_name():
    return {"win32": "win", "linux": "linux", "darwin": "osx"}[sys.platform]


package_root = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def import_ti_python_core():
    from .core import _infernux_gpu_compiler as core
    return core


def is_ci():
    return os.environ.get("TI_CI", "") == "1"


def get_core_shared_object():
    return ti_python_core.__file__


def print_red_bold(*args, **kwargs):
    print(*args, **kwargs)


def print_yellow_bold(*args, **kwargs):
    print(*args, **kwargs)


def check_exists(src):
    if not os.path.exists(src):
        raise FileNotFoundError(src)


def get_dll_name(name):
    if sys.platform == "win32":
        return f"taichi_{name}.dll"
    if sys.platform == "linux":
        return f"libtaichi_{name}.so"
    raise RuntimeError(f"Unsupported compiler library platform: {sys.platform}")


ti_python_core = import_ti_python_core()

log_level = os.environ.get("TI_LOG_LEVEL", "")
if log_level:
    ti_python_core.set_logging_level(log_level)
