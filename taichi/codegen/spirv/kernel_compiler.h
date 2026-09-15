#pragma once

#include <memory>

#include "taichi/program/kernel.h"
#include "taichi/program/compile_config.h"
#include "taichi/rhi/device_capability.h"
#include "taichi/codegen/spirv/compiled_kernel_data.h"

namespace taichi::lang {
namespace spirv {

// A stateless transformation, not a selectable execution backend.
class KernelCompiler final {
 public:
  using IRNodePtr = std::unique_ptr<IRNode>;
  using CKDPtr = std::unique_ptr<CompiledKernelData>;

  IRNodePtr compile(const CompileConfig &compile_config,
                    const Kernel &kernel_def) const;

  CKDPtr compile(const CompileConfig &compile_config,
                 const DeviceCapabilityConfig &device_caps,
                 const Kernel &kernel_def,
                 IRNode &chi_ir) const;
};

}  // namespace spirv
}  // namespace taichi::lang
