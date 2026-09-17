#include "compile_config.h"

#include <thread>
#include "taichi/rhi/arch.h"

namespace taichi::lang {

CompileConfig::CompileConfig() {
  arch = Arch::vulkan;
  opt_level = 1;
  external_optimization_level = 3;
  print_ir = false;
  print_preprocessed_ir = false;
  print_ir_dbg_info = false;
  demote_dense_struct_fors = true;
  advanced_optimization = true;
  constant_folding = true;
  debug = false;
  cfg_optimization = true;
  check_out_of_bound = false;
  simplify_before_lower_access = true;
  lower_access = true;
  simplify_after_lower_access = true;
  move_loop_invariant_outside_if = false;
  default_fp = PrimitiveType::f32;
  default_ip = PrimitiveType::i32;
  default_up = PrimitiveType::u32;
  default_cpu_block_dim = 32;
  cpu_block_dim_adaptive = true;
  default_gpu_block_dim = 128;
  verbose = true;
  fast_math = true;
  flatten_if = false;
  make_thread_local = true;
  make_block_local = true;
  detect_read_only = true;
  real_matrix_scalarize = true;
  force_scalarize_matrix = false;
  half2_vectorization = false;
  make_cpu_multithreading_loop = true;

  saturating_grid_dim = 0;
  max_block_dim = 0;
  cpu_max_num_threads = std::thread::hardware_concurrency();
}

}  // namespace taichi::lang
