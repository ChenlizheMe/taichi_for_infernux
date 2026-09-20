# ./taichi/util/CMakeLists.txt
# Modified by Infernux: exclude the embedded test runner and LLVM include path.

add_library(taichi_util)
target_sources(taichi_util
  PRIVATE
    bit.cpp
    lang_util.cpp
    short_name.cpp
    str.cpp
  )

target_include_directories(taichi_util
  PRIVATE
    ${PROJECT_SOURCE_DIR}
    ${PROJECT_SOURCE_DIR}/external/include
    ${PROJECT_SOURCE_DIR}/external/eigen
  )

target_link_libraries(taichi_util PUBLIC taichi_common)
