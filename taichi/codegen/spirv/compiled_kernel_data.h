#pragma once

#include "taichi/codegen/spirv/kernel_utils.h"
#include "taichi/rhi/device_capability.h"

namespace taichi::lang {

namespace spirv {

// Compiler output only. Infernux owns artifact files/caching and execution.
class CompiledKernelData final {
 public:
  struct InternalData {
    using TaskCode = std::vector<uint32_t>;
    using TasksCode = std::vector<TaskCode>;

    // meta data
    struct Metadata {
      TaichiKernelAttributes kernel_attribs;
      // Exact target contract used while producing the module.  This is
      // compiler output metadata only; it never owns or probes a device.
      DeviceCapabilityConfig required_capabilities;
    } metadata;
    // source code
    struct Source {
      TasksCode spirv_src;
    } src;
  };

  explicit CompiledKernelData(InternalData data) : data_(std::move(data)) {
  }

  const InternalData &get_internal_data() const {
    return data_;
  }

 private:
  InternalData data_;
};

}  // namespace spirv

}  // namespace taichi::lang
