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

# This is an intentionally closed compiler source set.  Do not replace it with
# directory globs: the upstream directories also contain execution runtimes,
# registries, signal handlers, profiling UI, SNode layout managers, and other
# facilities that are not part of Python AST -> SPIR-V compilation.
set(TAICHI_CORE_SOURCE
    "${PROJECT_SOURCE_DIR}/taichi/analysis/alias_analysis.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/arithmetic_interpretor.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/bls_analyzer.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/build_cfg.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/check_fields_registered.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/clone.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/constexpr_propagation.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/count_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/data_source_analysis.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/detect_fors_with_break.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_deactivations.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_dynamically_indexed_pointers.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_func_store_dests.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_immutable_local_vars.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_mesh_thread_local.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_meshfor_relation_types.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_snode_read_writes.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_statement_usages.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_uniquely_accessed_pointers.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/gather_used_atomics.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/has_store_or_atomic.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/last_store_or_atomic.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/mesh_bls_analyzer.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/same_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/value_diff.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/analysis/verify.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/basic_stmt_visitor.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/control_flow_graph.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/expr.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/expression_ops.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/frontend_ir.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/ir_builder.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/ir.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/mesh.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/offloaded_task_type.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/pass.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/scratch_pad.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/snode_types.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/snode.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/stmt_op_types.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/type_factory.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/type_system.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/type_utils.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/ir/type.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/callable.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/compile_config.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/extension.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/function_key.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/function.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/kernel.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/program.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/program/snode_expr_utils.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/rhi/arch.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/rhi/device_capability.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/system/demangling.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/system/profiler.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/system/timer.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/alg_simp.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/auto_diff.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/binary_op_simplify.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/bit_loop_vectorize.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/cache_loop_invariant_global_vars.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/cfg_optimization.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/check_out_of_bound.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/compile_taichi_functions.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/compile_to_offloads.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/constant_fold.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/demote_atomics.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/demote_dense_struct_fors.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/demote_mesh_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/demote_no_access_mesh_fors.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/demote_operations.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/detect_read_only.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/determine_ad_stack_size.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/die.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/eliminate_immutable_local_vars.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/extract_constant.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/flag_access.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/frontend_type_check.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/handle_external_ptr_boundary.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/inlining.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/insert_scratch_pad.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/ir_printer.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/loop_invariant_code_motion.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/lower_access.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/lower_ast.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/lower_matrix_ptr.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/make_block_local.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/make_cpu_multithreaded_range_for.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/make_mesh_block_local.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/make_mesh_thread_local.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/make_thread_local.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/offload.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/optimize_bit_struct_stores.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/re_id.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/remove_assume_in_range.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/remove_loop_unique.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/replace_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/reverse_segments.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/scalar_pointer_lowerer.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/scalarize.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/simplify.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/statement_usage_replace.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/transform_statements.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/type_check.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/unreachable_code_elimination.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/utils.cpp"
    "${PROJECT_SOURCE_DIR}/taichi/transforms/whole_kernel_cse.cpp"
)

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
    set(CORE_WITH_PYBIND_LIBRARY_NAME _infernux_gpu_compiler)
    if (NOT ANDROID)
        # NO_EXTRAS is required here to avoid llvm symbol error during build
        set(TAICHI_PYBIND_SOURCE
            "${PROJECT_SOURCE_DIR}/taichi/python/exception.cpp"
            "${PROJECT_SOURCE_DIR}/taichi/python/export.cpp"
            "${PROJECT_SOURCE_DIR}/taichi/python/export_lang.cpp"
            "${PROJECT_SOURCE_DIR}/taichi/python/py_exception_translator.cpp"
        )
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
