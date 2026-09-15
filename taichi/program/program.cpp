// Modified for Infernux: compiler-only SPIR-V generation; no backend discovery,
// device, queue, allocation, launch runtime, or host floating-point mutation.

#include "program.h"

#include "taichi/ir/type_utils.h"
#include "taichi/program/extension.h"
#include "taichi/codegen/spirv/kernel_compiler.h"

namespace taichi::lang {

namespace {
std::tuple<const StructType *, size_t, size_t> apply_spirv_data_layout(
    const StructType *old_type,
    const std::string &layout) {
  TI_ASSERT(layout.size() == 2);
  const bool scalar_layout = layout[0] == '4';
  const bool physical_buffer_pointer = layout[1] == 'b';
  auto members = old_type->elements();
  size_t bytes = 0;
  size_t alignment = 0;
  for (auto &member : members) {
    size_t member_alignment = 0;
    size_t member_size = 0;
    if (auto *struct_type = member.type->cast<StructType>()) {
      auto [new_type, size, align] =
          apply_spirv_data_layout(struct_type, layout);
      member.type = new_type;
      member_alignment = align;
      member_size = size;
    } else if (auto *tensor_type = member.type->cast<TensorType>()) {
      const size_t element_size =
          data_type_size_gfx(tensor_type->get_element_type());
      const size_t element_count = tensor_type->get_num_elements();
      if (scalar_layout) {
        member_alignment = element_size;
        member_size = element_count * element_size;
      } else {
        member_alignment = element_size * (element_count == 2 ? 2 : 4);
        member_size = member_alignment;
      }
    } else if (member.type->is<PointerType>()) {
      member_size = physical_buffer_pointer ? sizeof(uint64_t) : sizeof(uint32_t);
      member_alignment = member_size;
    } else {
      TI_ASSERT(member.type->is<PrimitiveType>());
      member_size = data_type_size_gfx(member.type);
      member_alignment = member_size;
    }
    bytes = align_up(bytes, member_alignment);
    member.offset = bytes;
    bytes += member_size;
    alignment = std::max(alignment, member_alignment);
  }
  if (!scalar_layout) {
    alignment = align_up(alignment, sizeof(float) * 4);
    bytes = align_up(bytes, sizeof(float) * 4);
  }
  return {
      TypeFactory::get_instance().get_struct_type(members, layout)->as<StructType>(),
      bytes,
      alignment};
}
}  // namespace

Program::Program() {
  TI_TRACE("Program initializing as an Infernux compiler-only context...");

  auto &config = compile_config_;
  config = default_compile_config;
  config.arch = Arch::vulkan;
  config.fit();

  if (!is_extension_supported(config.arch, Extension::assertion)) {
    if (config.check_out_of_bound) {
      TI_WARN("Out-of-bound access checking is not supported on arch={}",
              arch_name(config.arch));
      config.check_out_of_bound = false;
    }
  }

  TI_TRACE("Program ({}) arch={} initialized.", fmt::ptr(this),
           arch_name(config.arch));
}

std::unique_ptr<spirv::CompiledKernelData> Program::compile_kernel(
    const CompileConfig &compile_config,
    const DeviceCapabilityConfig &caps,
    const Kernel &kernel_def) {
  const spirv::KernelCompiler compiler;
  auto ir = compiler.compile(compile_config, kernel_def);
  return compiler.compile(compile_config, caps, kernel_def, *ir);
}

DeviceCapabilityConfig Program::get_device_caps() const {
  DeviceCapabilityConfig caps;
  caps.set(DeviceCapability::spirv_version, 0x10300);
  return caps;
}

int Program::default_block_dim(const CompileConfig &config) {
  return config.default_gpu_block_dim;
}

std::pair<const StructType *, size_t> Program::get_struct_type_with_data_layout(
    const StructType *old_ty,
    const std::string &layout) {
  auto [new_type, size, alignment] = apply_spirv_data_layout(old_ty, layout);
  return {new_type, size};
}

}  // namespace taichi::lang
