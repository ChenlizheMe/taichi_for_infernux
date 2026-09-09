# Copyright (c) 2026 Infernux contributors. Apache-2.0.
# Product policy, not proof that all upstream runtime code has been removed.
foreach(feature C_API STATIC_C_API LLVM CUDA CUDA_TOOLKIT AMDGPU METAL OPENGL VULKAN DX11 DX12 GGUI)
    option(TI_WITH_${feature} "Unsupported in the Infernux compiler build" OFF)
    if(TI_WITH_${feature})
        message(FATAL_ERROR "taichi_for_infernux is JIT-only and uses engine-owned execution; TI_WITH_${feature} must be OFF")
    endif()
endforeach()
option(TI_BUILD_EXAMPLES "Build upstream examples" OFF)
option(TI_BUILD_RHI_EXAMPLES "Build upstream standalone RHI examples" OFF)
option(TI_WITH_PYTHON "Build the internal JIT compiler binding" ON)
