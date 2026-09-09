# Copyright (c) 2026 Infernux contributors. Apache-2.0.
# Used by the engine wheel build; no .inxpkg archive or project Package tree.
function(infernux_compiler_output target)
    if(NOT TARGET "${target}")
        message(FATAL_ERROR "Missing compiler binding target: ${target}")
    endif()
    set(INFERNUX_COMPILER_OUTPUT_DIR
        "${PROJECT_BINARY_DIR}/wheel/Infernux/_compiler/taichi"
        CACHE PATH "Native compiler destination inside the engine wheel staging tree")
    set_target_properties(${target} PROPERTIES
        LIBRARY_OUTPUT_DIRECTORY "${INFERNUX_COMPILER_OUTPUT_DIR}/$<0:>"
        RUNTIME_OUTPUT_DIRECTORY "${INFERNUX_COMPILER_OUTPUT_DIR}/$<0:>"
        ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/lib/$<0:>"
        PDB_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}/symbols/$<0:>")
    install(TARGETS ${target}
        RUNTIME DESTINATION Infernux/_compiler/taichi COMPONENT infernux_compiler
        LIBRARY DESTINATION Infernux/_compiler/taichi COMPONENT infernux_compiler)
    install(FILES "${PROJECT_SOURCE_DIR}/LICENSE" "${PROJECT_SOURCE_DIR}/NOTICE"
        DESTINATION Infernux/_compiler/licenses/taichi COMPONENT infernux_compiler)
endfunction()
