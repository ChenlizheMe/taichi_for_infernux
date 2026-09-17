/*******************************************************************************
    Copyright (c) The Taichi Authors (2016- ). All Rights Reserved.
    The use of this software is governed by the LICENSE file.
    Modified by the Infernux project in 2026: compute-only Python bindings.
*******************************************************************************/

#include "taichi/python/export.h"
#include "taichi/common/interface.h"

namespace taichi {

PYBIND11_MODULE(_infernux_gpu_compiler, m) {
  m.doc() = "Infernux private Python-to-SPIR-V compiler (derived from Taichi)";

  for (auto &kv : InterfaceHolder::get_instance()->methods) {
    kv.second(&m);
  }

  export_lang(m);
}

}  // namespace taichi
