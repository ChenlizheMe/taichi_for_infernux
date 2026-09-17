"""Infernux compiler source lookup using Python's standard source contract.

Modified from upstream Taichi: no Blender/IPython/REPL probing, temporary
source files, dill dependency or process-global inspect monkeypatches.
Dynamic source publishers must register their compilation filename in
linecache before compilation and retire it with the corresponding script.
"""

import inspect


def getsourcelines(obj):
    return inspect.getsourcelines(obj)


def getsourcefile(obj):
    filename = inspect.getsourcefile(obj)
    if filename is None:
        raise OSError("GPU JIT requires source registered by the script publisher")
    return filename


__all__ = ["getsourcelines", "getsourcefile"]
