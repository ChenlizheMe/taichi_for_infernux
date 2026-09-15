// Modified by Infernux: request-owned, device-independent SPIR-V context.

#pragma once

#include <functional>

#include "taichi/ir/frontend_ir.h"
#include "taichi/ir/ir.h"
#include "taichi/ir/type_factory.h"
#include "taichi/ir/snode.h"
#include "taichi/util/lang_util.h"
#include "taichi/program/callable.h"
#include "taichi/program/kernel.h"
#include "taichi/rhi/device_capability.h"

namespace taichi::lang {

namespace spirv {
class CompiledKernelData;
}

// Infernux GPU compilation context. A default-constructed Program is a
// compiler-only context: it lowers/codegens Vulkan kernels without a device,
// queue, runtime, ndarray, or field allocation.

class TI_DLL_EXPORT Program {
 public:
  using Kernel = taichi::lang::Kernel;

  Program();

  const CompileConfig &compile_config() const {
    return compile_config_;
  }

  std::unique_ptr<Kernel> kernel(
      const std::function<void(Kernel *)> &body,
      const std::string &name = "",
      AutodiffMode autodiff_mode = AutodiffMode::kNone) {
    // The compilation request owns its IR. Program is not a kernel cache.
    return std::make_unique<Kernel>(*this, body, name, autodiff_mode);
  }

  std::unique_ptr<spirv::CompiledKernelData> compile_kernel(
      const CompileConfig &compile_config,
      const DeviceCapabilityConfig &caps,
      const Kernel &kernel_def);

  DeviceCapabilityConfig get_device_caps() const;

  static int default_block_dim(const CompileConfig &config);

  std::string get_kernel_return_data_layout() {
    return "4-";
  };

  std::string get_kernel_argument_data_layout() {
    return "1-";
  };

  std::pair<const StructType *, size_t> get_struct_type_with_data_layout(
      const StructType *old_ty,
      const std::string &layout);

  Identifier get_next_global_id(const std::string &name = "") {
    return Identifier(global_id_counter_++, name);
  }

 private:
  CompileConfig compile_config_;

  int global_id_counter_{0};

};

}  // namespace taichi::lang
