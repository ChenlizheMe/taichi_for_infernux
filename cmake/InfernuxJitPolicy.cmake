# Copyright (c) 2026 Infernux contributors. Apache-2.0.
# Product policy, not proof that all upstream runtime code has been removed.
foreach(feature C_API STATIC_C_API LLVM CUDA CUDA_TOOLKIT AMDGPU METAL OPENGL VULKAN DX11 DX12 GGUI)
    option(TI_WITH_${feature} "Unsupported in the Infernux compiler build" OFF)
    if(TI_WITH_${feature})
        message(FATAL_ERROR "taichi_for_infernux is JIT-only and uses engine-owned execution; TI_WITH_${feature} must be OFF")
    endif()
endforeach()
foreach(feature TESTS EXAMPLES RHI_EXAMPLES)
    option(TI_BUILD_${feature} "Unsupported upstream runtime targets; use INFERNUX_BUILD_TESTS" OFF)
    if(TI_BUILD_${feature})
        message(FATAL_ERROR "taichi_for_infernux is a compiler dependency; TI_BUILD_${feature} must be OFF")
    endif()
endforeach()
option(TI_WITH_PYTHON "Build the internal JIT compiler binding" ON)

# The compiler is loaded only through its Python module initializer.  None of
# the upstream C++ classes form an engine ABI, so exporting them from the pyd
# would keep a second, accidental SDK alive and defeat the closed compiler
# boundary.  PYBIND11_MODULE exports PyInit__infernux_gpu_compiler itself.
add_compile_definitions(TI_INFERNUX_PRIVATE_COMPILER=1)
