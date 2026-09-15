# Modified by the Infernux project in 2026: incremental CPU bitcode build,
# without source-tree outputs or unused CUDA compilation paths.
set(runtime_bitcode "${CMAKE_CURRENT_BINARY_DIR}/runtime_${HOST_ARCH}.bc")
add_custom_command(
    OUTPUT "${runtime_bitcode}"
    COMMAND "${CLANG_EXECUTABLE}" -c "${CMAKE_CURRENT_SOURCE_DIR}/runtime.cpp"
            -o "${runtime_bitcode}" -fno-exceptions -emit-llvm -std=c++17
            -D "ARCH_${HOST_ARCH}" -I "${PROJECT_SOURCE_DIR}"
            -MD -MF "${runtime_bitcode}.d"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/runtime.cpp"
    DEPFILE "${runtime_bitcode}.d"
    VERBATIM
)
add_custom_target(generate_llvm_runtime DEPENDS "${runtime_bitcode}")
add_dependencies(${CORE_LIBRARY_NAME} generate_llvm_runtime)
install(FILES "${runtime_bitcode}" DESTINATION "${INSTALL_LIB_DIR}/runtime")
