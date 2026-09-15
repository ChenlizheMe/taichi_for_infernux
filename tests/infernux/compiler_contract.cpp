// Infernux compiler-only contracts. Real Vulkan execution belongs to the engine.
#include "taichi/program/program.h"
#include "taichi/codegen/spirv/compiled_kernel_data.h"
#include "taichi/ir/transforms.h"
#include "taichi/ir/analysis.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>

// Compile-time boundary: public compiler headers must not declare a competing
// runtime. These aliases deliberately conflict with even a forward declaration
// of the old RHI/LLVM types, catching accidental transitive includes.
namespace taichi::lang {
using Device = void;
using GraphicsDevice = void;
using DeviceAllocation = void;
using CommandList = void;
using Stream = void;
using RuntimeContext = void;
using LLVMRuntime = void;
}  // namespace taichi::lang

using namespace taichi::lang;
using taichi::Arch;

int main() {
  // Independent contexts may coexist; neither owns a device, queue or runtime.
  Program first_context;
  Program second_context;
  assert(first_context.compile_config().arch == Arch::vulkan);
  assert(second_context.compile_config().arch == Arch::vulkan);

  // Capabilities are supplied values, not a device query or allocation surface.
  DeviceCapabilityConfig caps;
  caps.set(DeviceCapability::spirv_version, 0x10300);
  auto copied_caps = caps;
  copied_caps.set(DeviceCapability::spirv_version, 0x10500);
  assert(caps.get(DeviceCapability::spirv_version) == 0x10300);
  assert(copied_caps.get(DeviceCapability::spirv_version) == 0x10500);
  assert(str2devcap("spirv_version") == DeviceCapability::spirv_version);

  auto &types = TypeFactory::get_instance();
  auto *f32 = types.get_primitive_type(PrimitiveTypeID::f32);
  auto *vector3 = types.get_tensor_type({3}, f32);
  auto *input = types.get_struct_type(
      {{f32, "head"}, {vector3, "vector"}, {f32, "tail"}})->as<StructType>();
  const auto [arguments, argument_bytes] =
      first_context.get_struct_type_with_data_layout(
          input, first_context.get_kernel_argument_data_layout());
  assert(argument_bytes == 48);
  assert(arguments->elements()[0].offset == 0);
  assert(arguments->elements()[1].offset == 16);
  assert(arguments->elements()[2].offset == 32);
  const auto [returns, return_bytes] =
      second_context.get_struct_type_with_data_layout(
          input, second_context.get_kernel_return_data_layout());
  assert(return_bytes == 20);
  assert(returns->elements()[0].offset == 0);
  assert(returns->elements()[1].offset == 4);
  assert(returns->elements()[2].offset == 16);
  assert(input->elements()[1].offset == 0); // Layout never mutates source types.

  // Output is a value, without backend discovery, runtime handles or TIC files.
  spirv::CompiledKernelData::InternalData data;
  data.src.spirv_src = {{0x07230203u, 0, 0, 0, 0}};
  spirv::CompiledKernelData output(data);
  data.src.spirv_src.clear();
  assert(output.get_internal_data().src.spirv_src.size() == 1);

  // Captured range bounds are metadata uses of statements in their body.
  // Both whole-root and upward use replacement must update them.
  Block root;
  auto task = Stmt::make<OffloadedStmt>(OffloadedTaskType::range_for, Arch::vulkan, nullptr);
  auto *offload = task->as<OffloadedStmt>();
  root.insert(std::move(task));
  auto *first = offload->body->insert(Stmt::make<ConstStmt>(TypedConstant(8)));
  auto *second = offload->body->insert(Stmt::make<ConstStmt>(TypedConstant(4)));
  offload->end_stmt = first;
  first->replace_usages_with(second);
  assert(offload->end_stmt == second);
  irpass::replace_all_usages_with(&root, second, first);
  assert(offload->end_stmt == first);
  // Task cloning must retain the bound and rebind it to the cloned body.
  offload->range_hint = "array extent";
  offload->set_tb("clone-test.py:17");
  auto cloned_task = irpass::analysis::clone(offload);
  auto *cloned_offload = cloned_task->as<OffloadedStmt>();
  assert(cloned_offload->end_stmt == cloned_offload->body->statements[0].get());
  assert(cloned_offload->range_hint == "array extent");
  assert(cloned_offload->get_tb() == "clone-test.py:17");

  // All task blocks must keep their statements, parent and cross-block uses.
  using TaskBlock = std::unique_ptr<Block> OffloadedStmt::*;
  const TaskBlock auxiliary_blocks[] = {
      &OffloadedStmt::tls_prologue, &OffloadedStmt::bls_prologue,
      &OffloadedStmt::mesh_prologue, &OffloadedStmt::bls_epilogue,
      &OffloadedStmt::tls_epilogue};
  for (auto member : auxiliary_blocks) {
    auto &block = offload->*member;
    block = std::make_unique<Block>();
    block->set_parent_stmt(offload);
    block->insert(Stmt::make<BinaryOpStmt>(BinaryOpType::add, first, second));
  }
  auto *index = offload->body->insert(Stmt::make<LoopIndexStmt>(offload, 0));
  auto cloned_root = irpass::analysis::clone(static_cast<IRNode *>(&root));
  auto *copy = cloned_root->as<Block>()->statements[0]->as<OffloadedStmt>();
  assert(copy->end_stmt == copy->body->statements[0].get());
  assert(copy->body->statements[2]->as<LoopIndexStmt>()->loop == copy);
  assert(index->as<LoopIndexStmt>()->loop == offload);
  for (auto member : auxiliary_blocks) {
    auto &block = copy->*member;
    assert(block && block->size() == 1 && block->get_parent() == copy);
    auto *sum = block->statements[0]->as<BinaryOpStmt>();
    assert(sum->lhs == copy->body->statements[0].get());
    assert(sum->rhs == copy->body->statements[1].get());
    assert(sum->lhs != first && sum->rhs != second);
  }
  auto repeated_clone = irpass::analysis::clone(copy);
  assert(repeated_clone->as<OffloadedStmt>()->end_stmt ==
         repeated_clone->as<OffloadedStmt>()->body->statements[0].get());
  root.statements.clear();
  assert(copy->end_stmt->as<ConstStmt>()->val.val_int32() == 8);
  assert(copy->body->statements[2]->as<LoopIndexStmt>()->loop == copy);
}
