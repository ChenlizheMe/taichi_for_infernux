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

Compiler-only conversion and wheel integration are **in progress**. This branch
establishes the repository identity, JIT policy and native wheel-output layout.
Upstream runtime/AOT source still needs removal; disabled targets do not prove
that this is finished. Local engine experiments are not all published here.
There is no validated end-to-end compiler wheel or Player release yet.

The planned engine API uses `inx.buffer`, `set_data/get_data`, lowercase
`inx.vector3`, CPU `@inx.jit.compile`, and GPU `@inx.compute.kernel` with
`inx.compute.launch`. These are migration targets, not a runnable quick start.

## Build integration

Engine contributors use the Infernux `infernux` conda environment. This
dependency belongs at `external/taichi_for_infernux`, outside `external/plugins`.
The `infernux-jit` CMake preset disables AOT C-API targets and unsupported
backends. Native output goes directly to
`build/infernux-jit/wheel/Infernux/_compiler/taichi`; the engine can set
`INFERNUX_COMPILER_OUTPUT_DIR` to its wheel staging location.

The `infernux_compiler` install component stages the native binding and notices.
Frontend/dependency collection and dual-JIT Player packaging still need work.
No `.inxpkg` target or independent Taichi wheel release is provided. Historical
upstream build scripts are not the Infernux release entry point.

CI checks the build policy and output contract on Windows/Linux, not full
compiler correctness. Native builds, integration and performance remain separate
acceptance requirements.

## License

Derived from [Taichi](https://github.com/taichi-dev/taichi), with thanks to its
authors and contributors. Original attribution is retained; see [LICENSE](LICENSE)
and [NOTICE](NOTICE). This is an Infernux-maintained fork, not an upstream release.
