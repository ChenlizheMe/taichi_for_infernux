#*********************************************************************
# The Taichi Programming Language
# Modified by the Infernux project in 2026 for engine-wheel JIT builds.
#*********************************************************************

cmake_minimum_required(VERSION 3.25)

project(taichi_for_infernux)

# Infernux modification: JIT-only engine dependency, not a plugin release.
include(cmake/InfernuxJitPolicy.cmake)

include("cmake/utils.cmake")

if (NOT DEFINED TI_VERSION_MAJOR)
    file(READ "${CMAKE_CURRENT_LIST_DIR}/version.txt" TI_VERSION_LITERAL)
    string(REGEX MATCH "v([0-9]+)\\.([0-9]+)\\.([0-9]+)" TI_VERSION_LITERAL ${TI_VERSION_LITERAL})
    set(TI_VERSION_MAJOR ${CMAKE_MATCH_1})
    set(TI_VERSION_MINOR ${CMAKE_MATCH_2})
    set(TI_VERSION_PATCH ${CMAKE_MATCH_3})
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED TRUE)
set(CMAKE_EXPORT_COMPILECOMMANDS ON)

execute_process(
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  COMMAND git rev-parse --short HEAD
  RESULT_VARIABLE SHORT_HASH_RESULT
  OUTPUT_VARIABLE TI_COMMIT_SHORT_HASH)
execute_process(
  WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
  COMMAND git rev-parse HEAD
  RESULT_VARIABLE SHORT_HASH_RESULT
  OUTPUT_VARIABLE TI_COMMIT_HASH)
string(STRIP ${TI_COMMIT_HASH} TI_COMMIT_HASH)
string(STRIP ${TI_COMMIT_SHORT_HASH} TI_COMMIT_SHORT_HASH)

message("Taichi Version ${TI_VERSION_MAJOR}.${TI_VERSION_MINOR}.${TI_VERSION_PATCH}")
message("       Commit ${TI_COMMIT_HASH}")

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE "Release" CACHE STRING
            "Choose the type of build, options are: Debug Release
RelWithDebInfo MinSizeRel."
            FORCE)
endif(NOT CMAKE_BUILD_TYPE)

set(TAICHI_CMAKE_DIR "${CMAKE_CURRENT_LIST_DIR}/cmake/")

if (WIN32)
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake/")
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_ROOT}/Modules")
else ()
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_ROOT}/Modules")
    list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}/cmake/")
endif ()

set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/build")

find_program(CCACHE_PROGRAM ccache)
if(CCACHE_PROGRAM)
    set(CMAKE_CXX_COMPILER_LAUNCHER "${CCACHE_PROGRAM}")
endif()

# This compiles all the libraries with -fPIC, which is critical to link a static
# library into a shared lib.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)


option(USE_LLD "Use lld (from llvm) linker" OFF)
option(USE_MOLD "Use mold (A Modern Linker)" OFF)
option(TI_WITH_BACKTRACE "Use backward-cpp to print out C++ stack trace upon failure" OFF)  # wheel-tag: bt
option(TI_GENERATE_PDB "Generate Program Database (PDB) files (will make compilation uncacheable)" OFF)
option(TI_WITH_LTO "Enable Link Time Optimization (LTO) (affects Windows + MSVC for now)" OFF)  # wheel-tag: lto

if(LINUX OR APPLE)
    if (NOT IOS)
        # (penguinliong) Not compatible with -fembed-bitcode. Not sure where it
        # comes from; probably a XCode preset?
        set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -ffunction-sections -fdata-sections")
    endif()
endif()

if (USE_LLD)
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fuse-ld=lld")
    set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} -fuse-ld=lld")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fuse-ld=lld")

    if (WIN32)
        if (CMAKE_BUILD_TYPE EQUAL "RelWithDebInfo")
            # -debug for LLD generates PDB files
            set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -Wl,-debug")
            set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} -Wl,-debug")
            set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -Wl,-debug")
        endif()
    endif()
endif()

if (USE_MOLD)
    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -fuse-ld=mold")
    set(CMAKE_MODULE_LINKER_FLAGS "${CMAKE_MODULE_LINKER_FLAGS} -fuse-ld=mold")
    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -fuse-ld=mold")
endif()

# No support of Python for Android build; or in any case taichi is integrated
# in another project as submodule.
if (TI_WITH_PYTHON AND NOT ANDROID)
    find_package(Python 3.13 EXACT REQUIRED COMPONENTS Interpreter Development.Module NumPy)
    include(cmake/PythonNumpyPybind11.cmake)
else()
    # SPIR-V instruction tables require the same build interpreter even when
    # no Python extension is requested.
    find_package(Python 3.13 EXACT REQUIRED COMPONENTS Interpreter)
endif()

if (TI_WITH_BACKTRACE)
  add_subdirectory(external/backward_cpp)
endif()

if (TI_DISTRIBUTED_COMPILE)
    include(cmake/Distributed.cmake)
endif()

include(cmake/TaichiCXXFlags.cmake)
include(cmake/TaichiCore.cmake)

option(TI_BUILD_TESTS "Build the CPP tests" OFF)

if (TI_BUILD_TESTS)
  add_subdirectory(external/googletest EXCLUDE_FROM_ALL)
  include(cmake/TaichiTests.cmake)
endif()

message("C++ Flags: ${CMAKE_CXX_FLAGS}")
message("Build type: ${CMAKE_BUILD_TYPE}")

if (NOT TI_WITH_CUDA)
    set(CUDA_VERSION "0.0")
    set(CUDA_TOOLKIT_ROOT_DIR "")
endif()

if (TI_WITH_CUDA)
    set(CUDA_ARCH "cuda")
endif()

if (TI_WITH_AMDGPU)
    set(AMDGPU_ARCH "amdgpu")
endif()

if (TI_WITH_DX12)
    set(DX12_ARCH "dx12")
endif()

configure_file(taichi/common/version.h.in ${CMAKE_SOURCE_DIR}/taichi/common/version.h)
configure_file(taichi/common/commit_hash.h.in ${CMAKE_SOURCE_DIR}/taichi/common/commit_hash.h)

option(INFERNUX_BUILD_TESTS "Build engine-integration native contract tests" OFF)
if(INFERNUX_BUILD_TESTS)
  enable_testing()
  add_executable(infernux_compiler_contract_tests tests/infernux/compiler_contract.cpp)
  target_link_libraries(infernux_compiler_contract_tests PRIVATE ${CORE_LIBRARY_NAME})
  target_include_directories(infernux_compiler_contract_tests PRIVATE
    ${PROJECT_SOURCE_DIR} ${PROJECT_SOURCE_DIR}/external/eigen ${PROJECT_SOURCE_DIR}/external/spdlog/include)
  if(MSVC)
    target_compile_options(infernux_compiler_contract_tests PRIVATE /utf-8 /UNDEBUG)
  else()
    target_compile_options(infernux_compiler_contract_tests PRIVATE -UNDEBUG)
  endif()
  add_test(NAME infernux.compiler_contract COMMAND infernux_compiler_contract_tests)
  add_executable(infernux_bit_contract_tests tests/infernux/bit_contract.cpp)
  target_link_libraries(infernux_bit_contract_tests PRIVATE taichi_util)
  target_include_directories(infernux_bit_contract_tests PRIVATE ${PROJECT_SOURCE_DIR})
  if(MSVC)
    target_compile_options(infernux_bit_contract_tests PRIVATE /utf-8 /UNDEBUG)
  else()
    target_compile_options(infernux_bit_contract_tests PRIVATE -UNDEBUG)
  endif()
  add_test(NAME infernux.bit_contract COMMAND infernux_bit_contract_tests)
  set_target_properties(infernux_compiler_contract_tests infernux_bit_contract_tests PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/tests/$<CONFIG>")
endif()

include(cmake/InfernuxCompilerOutput.cmake)
if(TI_WITH_PYTHON AND NOT ANDROID)
    infernux_compiler_output(taichi_python)
endif()

option(TI_WITH_GRAPHVIZ "generate dependency graphs between targets" OFF)  # wheel-tag: viz
if (TI_WITH_GRAPHVIZ)
  set(GRAPHVIZ_GRAPH_NAME "ti_targets")
  add_custom_target(graphviz ALL
      COMMAND cp ${CMAKE_SOURCE_DIR}/cmake/CMakeGraphVizOptions.cmake .
      COMMAND ${CMAKE_COMMAND} "--graphviz=${GRAPHVIZ_GRAPH_NAME}.dot" .
      COMMAND dot -Tpng ${GRAPHVIZ_GRAPH_NAME}.dot -o ${GRAPHVIZ_GRAPH_NAME}.png
      COMMAND cp ti_targets.png ${CMAKE_SOURCE_DIR}/build
      WORKING_DIRECTORY "${CMAKE_BINARY_DIR}"
  )
endif()
