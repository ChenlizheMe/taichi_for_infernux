"""Evaluate the actual CMake flags module, including Windows cross-host cases."""
from pathlib import Path
import subprocess
import pytest


@pytest.mark.parametrize("compiler", ["MSVC", "Clang"])
@pytest.mark.parametrize("lto", ["ON", "OFF"])
def test_windows_release_retains_optimization_flags(tmp_path, compiler, lto):
    source = Path(__file__).resolve().parents[2] / "cmake/TaichiCXXFlags.cmake"
    project = tmp_path / "CMakeLists.txt"
    project.write_text(
        "cmake_minimum_required(VERSION 3.20)\nproject(Flags NONE)\n"
        "set(WIN32 TRUE)\nset(CMAKE_SYSTEM_PROCESSOR AMD64)\n"
        f"set(CMAKE_CXX_COMPILER_ID {compiler})\nset(MSVC {'TRUE' if compiler == 'MSVC' else 'FALSE'})\n"
        f"set(TI_WITH_LTO {lto})\n"
        'set(CMAKE_CXX_FLAGS_RELEASE "/O2 /DNDEBUG")\n'
        'set(CMAKE_CXX_FLAGS_RELWITHDEBINFO "/O2 /Zi /DNDEBUG")\n'
        f'include("{source.as_posix()}")\n'
        'if(NOT CMAKE_CXX_FLAGS_RELEASE MATCHES "/O2 /DNDEBUG")\n'
        'message(FATAL_ERROR "Release optimization was erased")\nendif()\n'
        'if(NOT CMAKE_CXX_FLAGS_RELWITHDEBINFO MATCHES "/O2 /Zi /DNDEBUG")\n'
        'message(FATAL_ERROR "RelWithDebInfo flags were erased")\nendif()\n'
        'if(NOT TI_WITH_LTO AND CMAKE_CXX_FLAGS_RELEASE MATCHES "flto|/GL")\n'
        'message(FATAL_ERROR "LTO enabled despite explicit OFF")\nendif()\n',
        encoding="utf-8",
    )
    result = subprocess.run(["cmake", "-S", str(tmp_path), "-B", str(tmp_path / "build")],
                            capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_private_frontend_install_excludes_retired_directories(tmp_path):
    """An incremental checkout can retain empty dirs or stale bytecode."""
    source = Path(__file__).resolve().parents[2] / "cmake/InfernuxCompilerOutput.cmake"
    frontend = tmp_path / "python/taichi"
    frontend.mkdir(parents=True)
    (frontend / "__init__.py").write_text("", encoding="utf-8")
    retired = ("ad", "aot", "graph", "shaders", "_snode", "_ti_module")
    for name in retired:
        folder = frontend / name
        folder.mkdir()
        # Include Python too: exclusions must not depend on extension filtering.
        (folder / "obsolete.py").write_text("", encoding="utf-8")
    for name in ("LICENSE", "NOTICE"):
        (tmp_path / name).write_text(name, encoding="utf-8")
    (tmp_path / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.25)\nproject(InstallContract NONE)\n"
        "add_library(compiler_contract INTERFACE)\n"
        f'include("{source.as_posix()}")\n'
        "infernux_compiler_output(compiler_contract)\n", encoding="utf-8")
    build, install = tmp_path / "build", tmp_path / "staged"
    for command in (
        ["cmake", "-S", str(tmp_path), "-B", str(build)],
        ["cmake", "--install", str(build), "--prefix", str(install),
         "--component", "infernux_compiler"],
    ):
        result = subprocess.run(command, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    vendor = install / "Infernux/_compiler/taichi/_vendor/taichi"
    assert (vendor / "__init__.py").is_file()
    assert all(not (vendor / name).exists() for name in retired)
    assert (install / "Infernux/_compiler/licenses/taichi/NOTICE").is_file()
