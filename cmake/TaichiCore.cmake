# Modified by the Infernux project in 2026 for engine-owned JIT compilation.
option(USE_STDCPP "Use -stdlib=libc++" OFF)
# Unsupported backend options are governed once by InfernuxJitPolicy.cmake.

# Force symbols to be 'hidden' by default so nothing is exported from the Taichi
# library including the third-party dependencies.
# As Taichi can be used by external projects, some of the internal dependencies
# such as Vulkan, ImGui, etc. could be in conflict with the dependencies of those
# projects.
set(CMAKE_CXX_VISIBILITY_PRESET hidden)
set(CMAKE_VISIBILITY_INLINES_HIDDEN ON)
# Suppress warnings from submodules introduced by the above symbol visibility change
set(CMAKE_POLICY_DEFAULT_CMP0063 NEW)
set(CMAKE_POLICY_DEFAULT_CMP0077 NEW)

if(UNIX AND NOT APPLE)
    # Handy helper for Linux
    # https://stackoverflow.com/a/32259072/12003165
    set(LINUX TRUE)
endif()

file(GLOB TAICHI_CORE_SOURCE
    "taichi/analysis/*.cpp" "taichi/analysis/*.h"
    "taichi/ir/*"
    "taichi/math/*"
    "taichi/program/*"
    "taichi/struct/*"
    "taichi/system/*"
    "taichi/transforms/*"
)
# These are value descriptions used by lowering, not a device API library.
# Allocation, transfer, command submission and synchronization belong to Infernux.
list(APPEND TAICHI_CORE_SOURCE
    "${PROJECT_SOURCE_DIR}/taichi/rhi/arch.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/rhi/device_capability.cpp")
list(FILTER TAICHI_CORE_SOURCE EXCLUDE REGEX "/system/run_tests\\.cpp$")
# Device-probe shims are intentionally not part of this source set. Vulkan
# capability and device ownership come from the Infernux RHI; keeping the
# optional backend directories out of the glob makes that boundary structural.

set(CORE_LIBRARY_NAME taichi_core)
add_library(${CORE_LIBRARY_NAME} OBJECT ${TAICHI_CORE_SOURCE})

target_include_directories(${CORE_LIBRARY_NAME} PRIVATE ${CMAKE_SOURCE_DIR})
target_include_directories(${CORE_LIBRARY_NAME} PRIVATE external/include)
target_include_directories(${CORE_LIBRARY_NAME} PRIVATE external/SPIRV-Tools/include)
target_include_directories(${CORE_LIBRARY_NAME} PRIVATE external/eigen)
target_include_directories(${CORE_LIBRARY_NAME} PRIVATE external/FP16/include)

add_subdirectory(taichi/util)
add_subdirectory(taichi/common)

target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE taichi_util)
target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE taichi_common)

# SPIR-V codegen is always there, regardless of Vulkan
set(SPIRV_SKIP_EXECUTABLES ON CACHE BOOL
    "Infernux compiler builds do not ship SPIR-V tools executables" FORCE)
set(SPIRV_SKIP_TESTS ON CACHE BOOL
    "Infernux compiler builds do not ship SPIR-V test targets" FORCE)
set(SPIRV-Headers_SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/SPIRV-Headers)
set(ENABLE_SPIRV_TOOLS_INSTALL OFF)
block(SCOPE_FOR VARIABLES)
    # This pinned compiler dependency predates CMake 4's policy minimum.
    set(CMAKE_POLICY_VERSION_MINIMUM 3.5)
    set(PYTHON_EXECUTABLE "${Python_EXECUTABLE}")
    # Only build libraries reached by spirv_codegen's link dependencies.
    # The upstream directory also defines diff/lint/reduce/link and a shared
    # tools DLL; none are part of the engine compiler or its default build.
    add_subdirectory(external/SPIRV-Tools EXCLUDE_FROM_ALL)
endblock()
add_subdirectory(taichi/codegen/spirv)

target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE spirv_codegen)


# Optional dependencies
if (APPLE)
    set(APPLE_FRAMEWORKS "")
    find_library(Foundation NAMES Foundation REQUIRED)
    find_library(Metal NAMES Metal REQUIRED)
    list(APPEND APPLE_FRAMEWORKS ${Foundation} ${Metal})
    if (NOT IOS)
        find_library(ApplicationServices NAMES ApplicationServices REQUIRED)
        find_library(Cocoa NAMES Cocoa REQUIRED)
        list(APPEND APPLE_FRAMEWORKS ${ApplicationServices} ${Cocoa})
    endif()
    target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE ${APPLE_FRAMEWORKS})
endif ()

if (ANDROID)
    # Android has a custom toolchain so pthread is not available and should
    # link against other libraries as well for logcat and internal features.
    target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE android log)
elseif (LINUX)
    target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE pthread)
    if (${CMAKE_HOST_SYSTEM_PROCESSOR} STREQUAL "x86_64")
        # Avoid glibc dependencies
        # Enforce compatibility with manylinux2014
        target_link_options(${CORE_LIBRARY_NAME} PRIVATE -Wl,--wrap=log2f -Wl,--wrap=exp2 -Wl,--wrap=log2 -Wl,--wrap=logf -Wl,--wrap=powf -Wl,--wrap=exp -Wl,--wrap=log -Wl,--wrap=pow)
    endif()
elseif (WIN32)
    target_link_libraries(${CORE_LIBRARY_NAME} PRIVATE Winmm)
endif()



foreach (source IN LISTS TAICHI_CORE_SOURCE)
    file(RELATIVE_PATH source_rel ${CMAKE_CURRENT_LIST_DIR} ${source})
    get_filename_component(source_path "${source_rel}" PATH)
    string(REPLACE "/" "\\" source_path_msvc "${source_path}")
    source_group("${source_path_msvc}" FILES "${source}")
endforeach ()

if(TI_WITH_PYTHON)
    set(CORE_WITH_PYBIND_LIBRARY_NAME taichi_python)
    if (NOT ANDROID)
        # NO_EXTRAS is required here to avoid llvm symbol error during build
        file(GLOB TAICHI_PYBIND_SOURCE
            "taichi/python/*.cpp"
            "taichi/python/*.h"
        )
        # Infernux owns diagnostics, math values, profiling and environment
        # policy. The compiler module exports language lowering only; do not
        # carry Taichi's CLI/benchmark/device-probe/image utility surface.
        list(FILTER TAICHI_PYBIND_SOURCE EXCLUDE REGEX
            "/export_math\\.cpp$")
        list(FILTER TAICHI_PYBIND_SOURCE EXCLUDE REGEX
            "/(interfaces_registry|memory_usage_monitor)\\.cpp$")
        pybind11_add_module(${CORE_WITH_PYBIND_LIBRARY_NAME} NO_EXTRAS ${TAICHI_PYBIND_SOURCE})
    else()
        add_library(${CORE_WITH_PYBIND_LIBRARY_NAME} SHARED)
    endif ()

    # Remove symbols from static libs: https://stackoverflow.com/a/14863432/12003165
    if (LINUX)
        target_link_options(${CORE_WITH_PYBIND_LIBRARY_NAME} PUBLIC -Wl,--exclude-libs=ALL)
        if (NOT ANDROID)
            # Excluding Android
            # Android defaults to static linking with libc++, no tinkering needed.
            target_link_options(${CORE_WITH_PYBIND_LIBRARY_NAME} PUBLIC -static-libgcc -static-libstdc++)
        endif()
    endif()

    if (TI_WITH_BACKTRACE)
        # Defined by external/backward-cpp:
        # This will add libraries, definitions and include directories needed by backward
        # by setting each property on the target.
        target_link_libraries(${CORE_WITH_PYBIND_LIBRARY_NAME} PRIVATE ${BACKWARD_ENABLE})
    endif()

    target_link_libraries(${CORE_WITH_PYBIND_LIBRARY_NAME} PRIVATE ${CORE_LIBRARY_NAME})

    target_include_directories(${CORE_WITH_PYBIND_LIBRARY_NAME}
      PRIVATE
        ${PROJECT_SOURCE_DIR}
        ${PROJECT_SOURCE_DIR}/external/spdlog/include
        ${PROJECT_SOURCE_DIR}/external/eigen
        ${PROJECT_SOURCE_DIR}/external/SPIRV-Tools/include
        ${PROJECT_SOURCE_DIR}/external/FP16/include
      )

    # These commands should apply to the DLL that is loaded from python, not the OBJECT library.
    if (MSVC)
        set_property(TARGET ${CORE_WITH_PYBIND_LIBRARY_NAME} APPEND PROPERTY LINK_FLAGS /DEBUG)
    endif ()

    # Output and installation belong solely to InfernuxCompilerOutput.cmake.
endif()
