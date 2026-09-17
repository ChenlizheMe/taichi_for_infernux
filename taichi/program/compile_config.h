// Modified by Infernux: per-context SPIR-V configuration, not runtime options.
#pragma once

#include "taichi/rhi/arch.h"
#include "taichi/util/lang_util.h"

namespace taichi::lang {

struct CompileConfig {
  Arch arch;
  bool debug;
  bool cfg_optimization;
  bool check_out_of_bound;
  int opt_level;
  int external_optimization_level;
  bool print_preprocessed_ir;
  bool print_ir;
  bool print_ir_dbg_info;
  bool simplify_before_lower_access;
  bool lower_access;
  bool simplify_after_lower_access;
  bool move_loop_invariant_outside_if;
  bool cache_loop_invariant_global_vars{true};
  bool demote_dense_struct_fors;
  bool advanced_optimization;
  bool constant_folding;
  bool verbose;
  bool fast_math;
  bool flatten_if;
  bool make_thread_local;
  bool make_block_local;
  bool detect_read_only;
  bool real_matrix_scalarize;
  bool force_scalarize_matrix;
  bool half2_vectorization;
  bool make_cpu_multithreading_loop;
  DataType default_fp;
  DataType default_ip;
  DataType default_up;
  int default_cpu_block_dim;
  bool cpu_block_dim_adaptive;
  int default_gpu_block_dim;
  int ad_stack_size{0};  // 0 = adaptive
  // The default size when the Taichi compiler is unable to automatically
  // determine the autodiff stack size.
  int default_ad_stack_size{32};

  int saturating_grid_dim;
  int max_block_dim;
  int cpu_max_num_threads;

  bool quant_opt_store_fusion{true};
  bool quant_opt_atomic_demotion{true};

  // Mesh related.
  // MeshTaichi options
  bool make_mesh_block_local{true};
  bool optimize_mesh_reordered_mapping{true};
  bool mesh_localize_to_end_mapping{true};
  bool mesh_localize_from_end_mapping{false};
  bool mesh_localize_all_attr_mappings{false};
  bool demote_no_access_mesh_fors{true};
  bool experimental_auto_mesh_local{false};
  int auto_mesh_local_default_occupacy{4};

  CompileConfig();
};

}  // namespace taichi::lang
