# Copyright (c) 2026 Infernux contributors. Apache-2.0.
# Used by the engine wheel build; no .inxpkg archive or project Package tree.
function(infernux_compiler_output target)
    if(NOT TARGET "${target}")
        message(FATAL_ERROR "Missing compiler binding target: ${target}")
    endif()
    set(INFERNUX_COMPILER_OUTPUT_DIR
        "${PROJECT_BINARY_DIR}/wheel/Infernux/_compiler/taichi/_vendor/taichi/_lib/core"
        CACHE PATH "Native compiler destination inside the engine wheel staging tree")
    set_target_properties(${target} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${INFERNUX_COMPILER_OUTPUT_DIR}/$<0:>"
        RUNTIME_OUTPUT_DIRECTORY "${INFERNUX_COMPILER_OUTPUT_DIR}/$<0:>"
        ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib/$<0:>"
        PDB_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/symbols/$<0:>")
    install(TARGETS ${target}
        RUNTIME DESTINATION Infernux/_compiler/taichi/_vendor/taichi/_lib/core COMPONENT infernux_compiler
        LIBRARY DESTINATION Infernux/_compiler/taichi/_vendor/taichi/_lib/core COMPONENT infernux_compiler)
    # The temporary lowering implementation lives below Infernux's private
    # compiler namespace. It is not a top-level taichi package and is loaded
    # only while an Infernux kernel is compiled. Source-level pruning proceeds
    # from this working main path; authors never receive Taichi containers/API.
    install(DIRECTORY "${PROJECT_SOURCE_DIR}/python/taichi/"
        DESTINATION Infernux/_compiler/taichi/_vendor/taichi
        COMPONENT infernux_compiler
        FILES_MATCHING PATTERN "*.py"
        PATTERN "__pycache__" EXCLUDE
        PATTERN "ad" EXCLUDE
        PATTERN "algorithms" EXCLUDE
        PATTERN "aot" EXCLUDE
        PATTERN "examples" EXCLUDE
        PATTERN "graph" EXCLUDE
        PATTERN "linalg" EXCLUDE
        PATTERN "math" EXCLUDE
        PATTERN "profiler" EXCLUDE
        PATTERN "simt" EXCLUDE
        PATTERN "sparse" EXCLUDE
        PATTERN "tools" EXCLUDE
        PATTERN "ui" EXCLUDE
        PATTERN "_snode" EXCLUDE
        PATTERN "_ti_module" EXCLUDE
        PATTERN "experimental.py" EXCLUDE
        PATTERN "misc.py" EXCLUDE
        PATTERN "quant.py" EXCLUDE
        PATTERN "_funcs.py" EXCLUDE
        PATTERN "_kernels.py" EXCLUDE
        PATTERN "__main__.py" EXCLUDE
        PATTERN "_main.py" EXCLUDE)
    install(FILES "${PROJECT_SOURCE_DIR}/LICENSE" "${PROJECT_SOURCE_DIR}/NOTICE"
        DESTINATION Infernux/_compiler/licenses/taichi COMPONENT infernux_compiler)
endfunction()
