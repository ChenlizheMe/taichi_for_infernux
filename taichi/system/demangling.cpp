/*******************************************************************************
    Copyright (c) The Taichi Authors (2016- ). All Rights Reserved.
    The use of this software is governed by the LICENSE file.
*******************************************************************************/

#include "taichi/common/core.h"
#if !defined(_WIN64)
#include <cxxabi.h>
#endif

namespace taichi {

// From https://en.wikipedia.org/wiki/Name_mangling

std::string cpp_demangle(const std::string &mangled_name) {
#if defined(TI_PLATFORM_UNIX)
  char *demangled_name;
  int status = -1;
  demangled_name =
      abi::__cxa_demangle(mangled_name.c_str(), nullptr, nullptr, &status);
  std::string ret(demangled_name);
  free(demangled_name);
  return ret;
#elif defined(TI_PLATFORM_WINDOWS)
  // Compiler diagnostics do not justify loading the Windows symbol engine.
  // Keep the original RTTI name; the error still identifies the statement.
  return mangled_name;
#else
  TI_NOT_IMPLEMENTED
#endif
}

}  // namespace taichi
