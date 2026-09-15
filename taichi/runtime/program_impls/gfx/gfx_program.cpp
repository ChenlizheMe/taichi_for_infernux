// Modified for Infernux: retain a host RHI adapter instead of creating a GPU.
#include "gfx_program.h"

#include "taichi/codegen/spirv/kernel_compiler.h"
#include "taichi/runtime/gfx/kernel_launcher.h"

namespace taichi::lang {

GfxProgramImpl::GfxProgramImpl(CompileConfig &config,
                               std::shared_ptr<Device> device)
    : ProgramImpl(config), device_(std::move(device)) {}

void GfxProgramImpl::materialize_runtime(KernelProfilerBase *profiler,
                                         uint64 **result_buffer_ptr) {
  TI_ASSERT_INFO(device_ != nullptr, "An engine compute device is required");
  TI_ASSERT_INFO(!runtime_, "Compute runtime is already materialized");
  gfx::GfxRuntime::Params params;
  params.device = device_.get();
  params.profiler = profiler;
  runtime_ = std::make_unique<gfx::GfxRuntime>(params);
  snode_tree_mgr_ = std::make_unique<gfx::SNodeTreeManager>(runtime_.get());
  *result_buffer_ptr = host_result_buffer_.data();
}

void GfxProgramImpl::enqueue_compute_op_lambda(
    std::function<void(Device *, CommandList *)> op,
    const std::vector<ComputeOpImageRef> &image_refs) {
  runtime_->enqueue_compute_op_lambda(std::move(op), image_refs);
}

void GfxProgramImpl::compile_snode_tree_types(SNodeTree *tree) {
  if (runtime_) {
    snode_tree_mgr_->materialize_snode_tree(tree);
  } else {
    gfx::CompiledSNodeStructs compiled_structs =
        gfx::compile_snode_structs(*tree->root());
    aot_compiled_snode_structs_.push_back(compiled_structs);
  }
}

void GfxProgramImpl::materialize_snode_tree(SNodeTree *tree,
                                            uint64 *result_buffer) {
  snode_tree_mgr_->materialize_snode_tree(tree);
}

DeviceAllocation GfxProgramImpl::allocate_memory_on_device(
    std::size_t alloc_size,
    uint64 *result_buffer) {
  DeviceAllocation alloc;
  RhiResult res = get_compute_device()->allocate_memory(
      {alloc_size, /*host_write=*/false, /*host_read=*/false,
       /*export_sharing=*/false},
      &alloc);
  TI_ASSERT(res == RhiResult::success);
  return alloc;
}

DeviceAllocation GfxProgramImpl::allocate_texture(const ImageParams &params) {
  return runtime_->create_image(params);
}

void GfxProgramImpl::finalize() {
  if (runtime_)
    runtime_->synchronize();
  snode_tree_mgr_.reset();
  runtime_.reset();
  device_.reset();
}

GfxProgramImpl::~GfxProgramImpl() {
  // Calling virtual methods in destructors is unsafe. Use static-binding here.
  GfxProgramImpl::finalize();
}

std::unique_ptr<KernelCompiler> GfxProgramImpl::make_kernel_compiler() {
  spirv::KernelCompiler::Config cfg;
  cfg.compiled_struct_data = runtime_ ? &snode_tree_mgr_->get_compiled_structs()
                                      : &aot_compiled_snode_structs_;
  return std::make_unique<spirv::KernelCompiler>(std::move(cfg));
}

std::unique_ptr<KernelLauncher> GfxProgramImpl::make_kernel_launcher() {
  gfx::KernelLauncher::Config cfg;
  cfg.gfx_runtime_ = runtime_.get();
  return std::make_unique<gfx::KernelLauncher>(std::move(cfg));
}

DeviceCapabilityConfig GfxProgramImpl::get_device_caps() {
  if (device_)
    return device_->get_caps();
  DeviceCapabilityConfig caps;
  caps.set(DeviceCapability::spirv_version, 0x10300);
  return caps;
}

}  // namespace taichi::lang
