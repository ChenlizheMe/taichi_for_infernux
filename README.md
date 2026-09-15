# Taichi for Infernux

[中文](README.zh-CN.md) · [Infernux engine](https://github.com/ChenlizheMe/Infernux) · [Upstream Taichi](https://github.com/taichi-dev/taichi)

This is the Taichi-derived GPU compiler dependency for **Infernux**, an
open-source game engine with a C++ runtime and Python gameplay code.
It is being integrated into the engine wheel, **not distributed as a project
plugin**. Game developers should not install a separate Taichi package.

## Direction

The current scope is JIT-only: translate engine numerical kernel code into
Vulkan SPIR-V and binding metadata. Infernux owns buffers, devices, allocation,
submission, synchronization and resource lifetime. This compiler must not own
`taichi.field`, SNode storage or a second Vulkan execution runtime.

CPU compilation remains an independent capability using Numba/llvmlite.
The engine and applicable Player builds will carry both CPU and GPU JIT tools.
AOT export and its standalone runtime are deferred.

## Status

Compiler-only conversion and release integration are **in progress**. The engine
build stages a private Python frontend and native SPIR-V compiler directly into
its wheel tree. Windows integration tests compile kernels without a GPU device
and execute their output through Infernux's Vulkan backend.

The active Python frontend no longer provides field/SNode storage owners,
device-array constructors or a kernel launch runtime. Its imports stay inside
`Infernux._compiler.taichi`; it does not claim the public `taichi` namespace.
Numeric Matrix/Vector expressions and the IR needed for code generation remain.
Kernel compilation consumes engine buffer type descriptions directly, without
allocating placeholder NumPy arrays. Each entry point creates one forward kernel;
automatic gradient kernels and class-method probing have been removed.
Engine-declared helper functions are lowered inline. The separate Taichi
function-specialization/call API and its Python/Program caches have been removed;
shared optimizer IR remains internal to the compiler.
Compiler kernels own their native IR and retain their context only while needed;
neither Python nor Program keeps a process-wide list of completed kernels.
Infernux retains the exported SPIR-V artifact, not the lowering objects or
generated-source entries used to produce it.
The native context calls the SPIR-V compiler directly, without a selectable
Program backend or a process-wide singleton lifetime. Its output is just code
and metadata: the old TIC serializer, payload hashing and execution handles are
removed. Artifact storage remains the engine's responsibility. This does not
make the shared Python frontend or type factory concurrently callable.
Compiler headers use texture-format and capability values without including a
device API. The legacy allocation/transfer/command implementation and its build
target have been removed; only Infernux performs those operations.
Native IR dependencies and unused upstream runtime/AOT source still need further
pruning. Disabled targets alone do not count as completed removal, and the full
cross-platform wheel and Player release matrix is not yet validated.

The engine integration uses `inx.buffer`, `set_data/get_data`, lowercase
`inx.vector3`, CPU `@inx.jit.compile`, and GPU `@inx.compute.kernel` with
`inx.compute.launch`. Those APIs belong to Infernux, not to this dependency;
there is no standalone Taichi authoring API to install from this repository.

## Build integration

Engine contributors use the Infernux `infernux` conda environment. This
dependency belongs at `external/taichi_for_infernux`, outside `external/plugins`.
The `infernux-jit` CMake preset disables AOT C-API targets and unsupported
backends. Native output goes directly to
`build/infernux-jit/wheel/Infernux/_compiler/taichi/_vendor/taichi/_lib/core`; the engine can set
`INFERNUX_COMPILER_OUTPUT_DIR` to its wheel staging location.

The `infernux_compiler` install component stages the native binding, the private
Python frontend, and LICENSE/NOTICE. The engine's `infernux_gpu_jit_compiler`
target builds and installs that payload without manual copying. Final
cross-platform dependency collection and dual-JIT Player packaging still need work.
No `.inxpkg` target or independent Taichi wheel release is provided. Historical
upstream build scripts are not the Infernux release entry point.

CI checks the build policy on Windows/Linux, builds a small native fixture and
installs the private frontend with LICENSE/NOTICE. This tests the wheel layout,
not full compiler correctness. Compiler builds, integration and performance
remain separate acceptance requirements.

The engine's `infernux.compute_compiler_only` CTest compiles from the installed
payload without loading the engine or creating a GPU device. Device execution is
covered separately by the engine's Vulkan integration tests.

## License

Derived from [Taichi](https://github.com/taichi-dev/taichi), with thanks to its
authors and contributors. Original attribution is retained; see [LICENSE](LICENSE)
and [NOTICE](NOTICE). This is an Infernux-maintained fork, not an upstream release.
