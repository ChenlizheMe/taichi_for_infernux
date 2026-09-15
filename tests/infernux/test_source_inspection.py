"""Verify source lookup through the private compiler without public Taichi."""

import importlib.util
import inspect
import linecache
from pathlib import Path

import pytest


source_file = Path(__file__).resolve().parents[2] / "python/taichi/lang/_wrap_inspect.py"
spec = importlib.util.spec_from_file_location("infernux_source_inspection", source_file)
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)


def sample_kernel(x):
    return x * x


def test_authored_source():
    assert lookup.getsourcelines(sample_kernel) == inspect.getsourcelines(sample_kernel)
    assert Path(lookup.getsourcefile(sample_kernel)) == Path(__file__)


def test_published_dynamic_source():
    filename = "<infernux-test-kernel:revision-1>"
    source = "def generated(x):\n    return x + 1\n"
    linecache.cache[filename] = (len(source), None, source.splitlines(True), filename)
    try:
        namespace = {}
        exec(compile(source, filename, "exec"), namespace)
        assert lookup.getsourcelines(namespace["generated"]) == (source.splitlines(True), 1)
        assert lookup.getsourcefile(namespace["generated"]) == filename
    finally:
        linecache.cache.pop(filename)


def test_unpublished_source_fails_without_global_patching():
    namespace = {}
    exec(compile("def generated(x): return x\n", "<unpublished-infernux-kernel>", "exec"), namespace)
    getfile, findsource = inspect.getfile, inspect.findsource
    with pytest.raises(OSError):
        lookup.getsourcelines(namespace["generated"])
    with pytest.raises(OSError, match="registered by the script publisher"):
        lookup.getsourcefile(namespace["generated"])
    assert inspect.getfile is getfile and inspect.findsource is findsource
