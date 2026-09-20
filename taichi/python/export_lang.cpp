// Bindings for the python frontend

#include <optional>
#include <string>
#include <algorithm>

#include "pybind11/functional.h"
#include "pybind11/pybind11.h"
#include "pybind11/eigen.h"
#include "pybind11/numpy.h"

#include "taichi/ir/expr.h"
#include "taichi/ir/expression_ops.h"
#include "taichi/ir/frontend_ir.h"
#include "taichi/ir/statements.h"
#include "taichi/codegen/spirv/compiled_kernel_data.h"
#include "taichi/program/extension.h"
#include "taichi/program/program.h"
#include "taichi/python/export.h"

namespace taichi {

void export_lang(py::module &m) {
  using namespace taichi::lang;
  using namespace std::placeholders;

  py::register_exception<TaichiTypeError>(m, "TaichiTypeError",
                                          PyExc_TypeError);
  py::register_exception<TaichiSyntaxError>(m, "TaichiSyntaxError",
                                            PyExc_SyntaxError);
  py::register_exception<TaichiIndexError>(m, "TaichiIndexError",
                                           PyExc_IndexError);
  py::register_exception<TaichiRuntimeError>(m, "TaichiRuntimeError",
                                             PyExc_RuntimeError);
  py::register_exception<TaichiAssertionError>(m, "TaichiAssertionError",
                                               PyExc_AssertionError);
  py::enum_<Arch>(m, "Arch", py::arithmetic())
#define PER_ARCH(x) .value(#x, Arch::x)
#include "taichi/inc/archs.inc.h"
#undef PER_ARCH
      .export_values();

  m.def("arch_name", arch_name);
  m.def("arch_from_name", arch_from_name);

  py::enum_<Extension>(m, "Extension", py::arithmetic())
#define PER_EXTENSION(x) .value(#x, Extension::x)
#include "taichi/inc/extensions.inc.h"
#undef PER_EXTENSION
      .export_values();

  py::enum_<ExternalArrayLayout>(m, "Layout", py::arithmetic())
      .value("AOS", ExternalArrayLayout::kAOS)
      .value("SOA", ExternalArrayLayout::kSOA)
      .value("NULL", ExternalArrayLayout::kNull)
      .export_values();

  py::enum_<BoundaryMode>(m, "BoundaryMode", py::arithmetic())
      .value("UNSAFE", BoundaryMode::kUnsafe)
      .value("CLAMP", BoundaryMode::kClamp)
      .export_values();

  // TODO(type): This should be removed
  py::class_<DataType>(m, "DataType")
      .def(py::init<Type *>())
      .def(py::self == py::self)
      .def("__hash__", &DataType::hash)
      .def("to_string", &DataType::to_string)
      .def("__str__", &DataType::to_string)
      .def("shape", &DataType::get_shape)
      .def("element_type", &DataType::get_element_type)
      .def("ptr_removed", &DataType::ptr_removed)
      .def(
          "get_ptr", [](DataType *dtype) -> Type * { return *dtype; },
          py::return_value_policy::reference)
      .def("__call__",
           [](DataType *dtype, py::args args, const py::kwargs &kwargs) {
             // Defining __call__ here to make DataType callable in Python,
             // which enables us to write `typing.Tuple[ti.i32, ti.i32]`.
             throw TaichiSyntaxError(
                 "Taichi data types cannot be called outside Taichi kernels.");
           })
      .def(py::pickle(
          [](const DataType &dt) {
            // Note: this only works for primitive types, which is fine for now.
            auto primitive =
                dynamic_cast<const PrimitiveType *>((const Type *)dt);
            TI_ASSERT(primitive);
            return py::make_tuple((std::size_t)primitive->type);
          },
          [](py::tuple t) {
            if (t.size() != 1)
              throw std::runtime_error("Invalid state!");

            DataType dt =
                PrimitiveType::get((PrimitiveTypeID)(t[0].cast<std::size_t>()));

            return dt;
          }));

  py::class_<DebugInfo>(m, "DebugInfo")
      .def(py::init<>())
      .def(py::init<std::string>())
      .def(py::init<>())
      .def_readwrite("tb", &DebugInfo::tb)
      .def_readwrite("src_loc", &DebugInfo::src_loc);

  py::class_<CompileConfig>(m, "CompileConfig")
      .def(py::init<>())
      .def_readwrite("arch", &CompileConfig::arch)
      .def_readwrite("opt_level", &CompileConfig::opt_level)
      .def_readwrite("print_ir", &CompileConfig::print_ir)
      .def_readwrite("print_preprocessed_ir",
                     &CompileConfig::print_preprocessed_ir)
      .def_readwrite("print_ir_dbg_info", &CompileConfig::print_ir_dbg_info)
      .def_readwrite("debug", &CompileConfig::debug)
      .def_readwrite("cfg_optimization", &CompileConfig::cfg_optimization)
      .def_readwrite("check_out_of_bound", &CompileConfig::check_out_of_bound)
      .def_readwrite("simplify_before_lower_access",
                     &CompileConfig::simplify_before_lower_access)
      .def_readwrite("simplify_after_lower_access",
                     &CompileConfig::simplify_after_lower_access)
      .def_readwrite("lower_access", &CompileConfig::lower_access)
      .def_readwrite("move_loop_invariant_outside_if",
                     &CompileConfig::move_loop_invariant_outside_if)
      .def_readwrite("cache_loop_invariant_global_vars",
                     &CompileConfig::cache_loop_invariant_global_vars)
      .def_readwrite("default_cpu_block_dim",
                     &CompileConfig::default_cpu_block_dim)
      .def_readwrite("cpu_block_dim_adaptive",
                     &CompileConfig::cpu_block_dim_adaptive)
      .def_readwrite("default_gpu_block_dim",
                     &CompileConfig::default_gpu_block_dim)
      .def_readwrite("saturating_grid_dim", &CompileConfig::saturating_grid_dim)
      .def_readwrite("max_block_dim", &CompileConfig::max_block_dim)
      .def_readwrite("cpu_max_num_threads", &CompileConfig::cpu_max_num_threads)
      .def_readwrite("verbose", &CompileConfig::verbose)
      .def_readwrite("demote_dense_struct_fors",
                     &CompileConfig::demote_dense_struct_fors)
      .def_readwrite("default_fp", &CompileConfig::default_fp)
      .def_readwrite("default_ip", &CompileConfig::default_ip)
      .def_readwrite("default_up", &CompileConfig::default_up)
      .def_readwrite("fast_math", &CompileConfig::fast_math)
      .def_readwrite("advanced_optimization",
                     &CompileConfig::advanced_optimization)
      .def_readwrite("ad_stack_size", &CompileConfig::ad_stack_size)
      .def_readwrite("flatten_if", &CompileConfig::flatten_if)
      .def_readwrite("make_thread_local", &CompileConfig::make_thread_local)
      .def_readwrite("make_block_local", &CompileConfig::make_block_local)
      .def_readwrite("detect_read_only", &CompileConfig::detect_read_only)
      .def_readwrite("real_matrix_scalarize",
                     &CompileConfig::real_matrix_scalarize)
      .def_readwrite("force_scalarize_matrix",
                     &CompileConfig::force_scalarize_matrix)
      .def_readwrite("half2_vectorization", &CompileConfig::half2_vectorization)
      .def_readwrite("make_cpu_multithreading_loop",
                     &CompileConfig::make_cpu_multithreading_loop)
      .def_readwrite("quant_opt_store_fusion",
                     &CompileConfig::quant_opt_store_fusion)
      .def_readwrite("quant_opt_atomic_demotion",
                     &CompileConfig::quant_opt_atomic_demotion)
      .def_readwrite("make_mesh_block_local",
                     &CompileConfig::make_mesh_block_local)
      .def_readwrite("mesh_localize_to_end_mapping",
                     &CompileConfig::mesh_localize_to_end_mapping)
      .def_readwrite("mesh_localize_from_end_mapping",
                     &CompileConfig::mesh_localize_from_end_mapping)
      .def_readwrite("optimize_mesh_reordered_mapping",
                     &CompileConfig::optimize_mesh_reordered_mapping)
      .def_readwrite("mesh_localize_all_attr_mappings",
                     &CompileConfig::mesh_localize_all_attr_mappings)
      .def_readwrite("demote_no_access_mesh_fors",
                     &CompileConfig::demote_no_access_mesh_fors)
      .def_readwrite("experimental_auto_mesh_local",
                     &CompileConfig::experimental_auto_mesh_local)
      .def_readwrite("auto_mesh_local_default_occupacy",
                     &CompileConfig::auto_mesh_local_default_occupacy);

  // Export ASTBuilder
  py::class_<ASTBuilder>(m, "ASTBuilder")
      .def("make_id_expr", &ASTBuilder::make_id_expr)
      .def("create_kernel_exprgroup_return",
           &ASTBuilder::create_kernel_exprgroup_return)
      .def("create_print", &ASTBuilder::create_print)
      .def("begin_func", &ASTBuilder::begin_func)
      .def("end_func", &ASTBuilder::end_func)
      .def("begin_frontend_if", &ASTBuilder::begin_frontend_if)
      .def("begin_frontend_if_true", &ASTBuilder::begin_frontend_if_true)
      .def("pop_scope", &ASTBuilder::pop_scope)
      .def("begin_frontend_if_false", &ASTBuilder::begin_frontend_if_false)
      .def("make_matrix_expr", &ASTBuilder::make_matrix_expr)
      .def("expr_alloca", &ASTBuilder::expr_alloca)
      .def("expr_alloca_shared_array", &ASTBuilder::expr_alloca_shared_array)
      .def("create_assert_stmt", &ASTBuilder::create_assert_stmt)
      .def("expr_assign", &ASTBuilder::expr_assign)
      .def("begin_frontend_range_for", &ASTBuilder::begin_frontend_range_for)
      .def("end_frontend_range_for", &ASTBuilder::pop_scope)
      .def("begin_frontend_struct_for_on_external_tensor",
           &ASTBuilder::begin_frontend_struct_for_on_external_tensor)
      .def("end_frontend_struct_for", &ASTBuilder::pop_scope)
      .def("begin_frontend_while", &ASTBuilder::begin_frontend_while)
      .def("insert_break_stmt", &ASTBuilder::insert_break_stmt)
      .def("insert_continue_stmt", &ASTBuilder::insert_continue_stmt)
      .def("insert_expr_stmt", &ASTBuilder::insert_expr_stmt)
      .def("insert_thread_idx_expr", &ASTBuilder::insert_thread_idx_expr)
      .def("expand_exprs", &ASTBuilder::expand_exprs)
      .def("expr_subscript", &ASTBuilder::expr_subscript)
      .def("expr_var", &ASTBuilder::make_var)
      .def("strictly_serialize", &ASTBuilder::strictly_serialize)
      .def("block_dim", &ASTBuilder::block_dim);

  py::class_<DeviceCapabilityConfig>(
      m, "DeviceCapabilityConfig");  // NOLINT(bugprone-unused-raii)

  py::class_<spirv::CompiledKernelData>(m, "CompiledKernelData")
      .def_property_readonly(
          "_infernux_spirv_tasks",
          [](const spirv::CompiledKernelData &compiled) {
            py::list result;
            for (const auto &task : compiled.get_internal_data().src.spirv_src)
              result.append(
                  py::bytes(reinterpret_cast<const char *>(task.data()),
                            task.size() * sizeof(uint32_t)));
            return result;
          })
      .def_property_readonly(
          "_infernux_task_metadata",
          [](const spirv::CompiledKernelData &compiled) {
            using BufferType = spirv::TaskAttributes::BufferType;
            py::list result;
            const auto &array_accesses =
                compiled.get_internal_data()
                    .metadata.kernel_attribs.ctx_attribs.arr_access;
            for (const auto &task :
                 compiled.get_internal_data()
                     .metadata.kernel_attribs.tasks_attribs) {
              py::dict item;
              item["name"] = task.name;
              item["entry_point"] = task.name;
              item["total_threads"] = task.advisory_total_num_threads;
              item["threads_per_group"] = task.advisory_num_threads_per_group;
              item["workgroup_size"] = py::make_tuple(
                  task.advisory_num_threads_per_group, 1, 1);
              py::list bindings;
              for (const auto &binding : task.buffer_binds) {
                py::dict value;
                value["binding"] = binding.binding;
                switch (binding.buffer.type) {
                  case BufferType::Args:
                    value["resource_kind"] = "arguments";
                    value["binding_type"] = "uniform";
                    break;
                  case BufferType::ArgPack:
                    value["resource_kind"] = "argument_pack";
                    value["binding_type"] = "uniform";
                    break;
                  case BufferType::ExtArr:
                    value["resource_kind"] = "external_buffer";
                    value["binding_type"] = "storage";
                    for (const auto &[indices, access] : array_accesses) {
                      if (indices == binding.buffer.root_id) {
                        value["access"] = static_cast<uint32_t>(access);
                        break;
                      }
                    }
                    break;
                  case BufferType::Rets:
                    value["resource_kind"] = "returns";
                    value["binding_type"] = "storage";
                    break;
                  case BufferType::Root:
                    value["resource_kind"] = "root";
                    value["binding_type"] = "storage";
                    break;
                  case BufferType::GlobalTmps:
                    value["resource_kind"] = "global_temporaries";
                    value["binding_type"] = "storage";
                    break;
                  case BufferType::ListGen:
                    value["resource_kind"] = "list_generation";
                    value["binding_type"] = "storage";
                    break;
                }
                value["argument_indices"] = binding.buffer.root_id;
                bindings.append(std::move(value));
              }
              item["buffer_bindings"] = std::move(bindings);
              result.append(std::move(item));
            }
            return result;
          })
      .def_property_readonly(
          "_infernux_required_capabilities",
          [](const spirv::CompiledKernelData &compiled) {
            py::dict result;
            for (const auto &[capability, level] :
                 compiled.get_internal_data()
                     .metadata.required_capabilities.to_inner()) {
              result[py::str(to_string(capability))] = level;
            }
            return result;
          });

  py::class_<Program>(m, "Program")
      .def(py::init<>())
      .def("config", &Program::compile_config,
           py::return_value_policy::reference_internal)
      .def(
          "create_kernel",
          [](Program *program, const std::string &name) {
            py::gil_scoped_release release;
            // Publish the owning Python handle before Python AST lowering.
            // A retained error traceback must never contain a half-constructed
            // native Kernel that was deleted by a throwing constructor.
            return program->kernel([](Kernel *) {}, name);
          },
          py::keep_alive<0, 1>())
      .def("compile_kernel", &Program::compile_kernel,
           py::return_value_policy::move)
      .def("get_device_caps", &Program::get_device_caps);

  py::class_<Kernel>(m, "Kernel")
      .def("insert_scalar_param", &Kernel::insert_scalar_param)
      .def("insert_ndarray_param", &Kernel::insert_ndarray_param)
      .def("insert_pointer_param", &Kernel::insert_pointer_param)
      .def("insert_ret", &Kernel::insert_ret)
      .def("finalize_rets", &Kernel::finalize_rets)
      .def("finalize_params", &Kernel::finalize_params)
      .def_property_readonly(
          "_infernux_argument_layout",
          [](const Kernel &kernel) {
            if (!kernel.args_type)
              throw std::invalid_argument(
                  "Kernel parameters must be finalized before layout export");
            py::dict result;
            result["size"] = kernel.args_size;
            py::list parameters;
            for (size_t index = 0; index < kernel.parameter_list.size();
                 ++index) {
              const auto &parameter = kernel.parameter_list[index];
              py::dict item;
              if (parameter.is_array) {
                item["kind"] = "external_buffer";
                py::list shape_offsets;
                const auto runtime_rank =
                    parameter.total_dim - parameter.element_shape.size();
                for (size_t axis = 0; axis < runtime_rank; ++axis) {
                  shape_offsets.append(kernel.args_type->get_element_offset(
                      {static_cast<int>(index), 0, static_cast<int>(axis)}));
                }
                item["shape_offsets"] = std::move(shape_offsets);
                item["byte_offset_offset"] =
                    kernel.args_type->get_element_offset(
                        {static_cast<int>(index), 1});
              } else {
                const auto dtype = parameter.get_dtype();
                if (dtype->is_primitive(PrimitiveTypeID::i32))
                  item["kind"] = "int32";
                else if (dtype->is_primitive(PrimitiveTypeID::f32))
                  item["kind"] = "float32";
                else
                  throw std::invalid_argument(
                      "Infernux kernel parameters support only int32 and "
                      "float32 scalars");
                item["offset"] = kernel.args_type->get_element_offset(
                    {static_cast<int>(index)});
              }
              parameters.append(std::move(item));
            }
            result["parameters"] = std::move(parameters);
            return result;
          })
      .def(
          "ast_builder",
          [](Kernel *self) -> ASTBuilder * {
            return &self->context->builder();
          },
          py::return_value_policy::reference_internal);

  py::class_<Expr> expr(m, "Expr");
  expr.def("is_external_tensor_expr",
           [](Expr *expr) { return expr->is<ExternalTensorExpression>(); })
      .def("is_index_expr",
           [](Expr *expr) { return expr->is<IndexExpression>(); })
      .def("is_lvalue", [](Expr *expr) { return expr->expr->is_lvalue(); })
      .def("set_dbg_info", &Expr::set_dbg_info)
      .def("get_dbg_info", [](Expr *expr) { return expr->expr->dbg_info; })
      .def("get_ret_type", &Expr::get_ret_type)
      .def("get_rvalue_type",
           [](Expr *expr) { return expr->get_rvalue_type(); })
      .def("is_tensor",
           [](Expr *expr) { return expr->get_rvalue_type()->is<TensorType>(); })
      .def("is_struct",
           [](Expr *expr) { return expr->get_rvalue_type()->is<StructType>(); })
      .def("get_shape",
           [](Expr *expr) -> std::optional<std::vector<int>> {
             auto tensor_type = expr->get_rvalue_type()->cast<TensorType>();
             if (tensor_type) {
               return std::optional<std::vector<int>>(tensor_type->get_shape());
             }
             return std::nullopt;
           })
      .def("type_check", &Expr::type_check)
      .def("get_raw_address", [](Expr *expr) { return (uint64)expr; })
      .def("get_underlying_ptr_address", [](Expr *e) {
        // The reason that there are both get_raw_address() and
        // get_underlying_ptr_address() is that Expr itself is mostly wrapper
        // around its underlying |expr| (of type Expression). Expr |e| can be
        // temporary, while the underlying |expr| is mostly persistent.
        //
        // Same get_raw_address() implies that get_underlying_ptr_address() are
        // also the same. The reverse is not true.
        return (uint64)e->expr.get();
      });

  py::class_<ExprGroup>(m, "ExprGroup")
      .def(py::init<>())
      .def("size", [](ExprGroup *eg) { return eg->exprs.size(); })
      .def("push_back", &ExprGroup::push_back);

  py::class_<Stmt>(m, "Stmt");  // NOLINT(bugprone-unused-raii)

  m.def("insert_internal_func_call", [&](Operation *op, const ExprGroup &args) {
    return Expr::make<InternalFuncCallExpression>(op, args.exprs);
  });

  m.def("make_get_element_expr",
        Expr::make<GetElementExpression, const Expr &, std::vector<int>,
                   const DebugInfo &>);

  m.def("value_cast", static_cast<Expr (*)(const Expr &expr, DataType)>(cast));
  m.def("bits_cast",
        static_cast<Expr (*)(const Expr &expr, DataType)>(bit_cast));

  m.def("expr_atomic_add", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::add, a, b);
  });

  m.def("expr_atomic_sub", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::sub, a, b);
  });

  m.def("expr_atomic_min", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::min, a, b);
  });

  m.def("expr_atomic_max", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::max, a, b);
  });

  m.def("expr_atomic_bit_and", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::bit_and, a, b);
  });

  m.def("expr_atomic_bit_or", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::bit_or, a, b);
  });

  m.def("expr_atomic_bit_xor", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::bit_xor, a, b);
  });

  m.def("expr_atomic_mul", [&](const Expr &a, const Expr &b) {
    return Expr::make<AtomicOpExpression>(AtomicOpType::mul, a, b);
  });

  m.def("expr_assume_in_range", assume_range);

  m.def("expr_loop_unique", loop_unique);

#define DEFINE_EXPRESSION_OP(x) m.def("expr_" #x, expr_##x);

  DEFINE_EXPRESSION_OP(neg)
  DEFINE_EXPRESSION_OP(sqrt)
  DEFINE_EXPRESSION_OP(round)
  DEFINE_EXPRESSION_OP(floor)
  DEFINE_EXPRESSION_OP(frexp)
  DEFINE_EXPRESSION_OP(ceil)
  DEFINE_EXPRESSION_OP(abs)
  DEFINE_EXPRESSION_OP(sin)
  DEFINE_EXPRESSION_OP(asin)
  DEFINE_EXPRESSION_OP(cos)
  DEFINE_EXPRESSION_OP(acos)
  DEFINE_EXPRESSION_OP(tan)
  DEFINE_EXPRESSION_OP(tanh)
  DEFINE_EXPRESSION_OP(inv)
  DEFINE_EXPRESSION_OP(rcp)
  DEFINE_EXPRESSION_OP(rsqrt)
  DEFINE_EXPRESSION_OP(exp)
  DEFINE_EXPRESSION_OP(log)
  DEFINE_EXPRESSION_OP(popcnt)
  DEFINE_EXPRESSION_OP(clz)

  DEFINE_EXPRESSION_OP(select)
  DEFINE_EXPRESSION_OP(ifte)

  DEFINE_EXPRESSION_OP(cmp_le)
  DEFINE_EXPRESSION_OP(cmp_lt)
  DEFINE_EXPRESSION_OP(cmp_ge)
  DEFINE_EXPRESSION_OP(cmp_gt)
  DEFINE_EXPRESSION_OP(cmp_ne)
  DEFINE_EXPRESSION_OP(cmp_eq)

  DEFINE_EXPRESSION_OP(bit_and)
  DEFINE_EXPRESSION_OP(bit_or)
  DEFINE_EXPRESSION_OP(bit_xor)
  DEFINE_EXPRESSION_OP(bit_shl)
  DEFINE_EXPRESSION_OP(bit_shr)
  DEFINE_EXPRESSION_OP(bit_sar)
  DEFINE_EXPRESSION_OP(bit_not)

  DEFINE_EXPRESSION_OP(logic_not)
  DEFINE_EXPRESSION_OP(logical_and)
  DEFINE_EXPRESSION_OP(logical_or)

  DEFINE_EXPRESSION_OP(add)
  DEFINE_EXPRESSION_OP(sub)
  DEFINE_EXPRESSION_OP(mul)
  DEFINE_EXPRESSION_OP(div)
  DEFINE_EXPRESSION_OP(truediv)
  DEFINE_EXPRESSION_OP(floordiv)
  DEFINE_EXPRESSION_OP(mod)
  DEFINE_EXPRESSION_OP(max)
  DEFINE_EXPRESSION_OP(min)
  DEFINE_EXPRESSION_OP(atan2)
  DEFINE_EXPRESSION_OP(pow)

#undef DEFINE_EXPRESSION_OP

  m.def("make_arg_load_expr",
        Expr::make<ArgLoadExpression, const std::vector<int> &,
                   const DataType &, bool, bool, int, const DebugInfo &>,
        "arg_id"_a, "dt"_a, "is_ptr"_a = false, "create_load"_a = true,
        "arg_depth"_a = 0, "dbg_info"_a = DebugInfo());

  m.def("make_reference",
        Expr::make<ReferenceExpression, const Expr &, const DebugInfo &>);

  m.def("make_external_tensor_expr",
        Expr::make<ExternalTensorExpression, const DataType &, int,
                   const std::vector<int> &, bool, int, const BoundaryMode &>);

  m.def("make_rand_expr",
        Expr::make<RandExpression, const DataType &, const DebugInfo &>);

  m.def("make_const_expr_bool",
        Expr::make<ConstExpression, const DataType &, uint1>);

  m.def("make_const_expr_int",
        Expr::make<ConstExpression, const DataType &, int64>);

  m.def("make_const_expr_fp",
        Expr::make<ConstExpression, const DataType &, float64>);

  auto &&bin = py::enum_<BinaryOpType>(m, "BinaryOpType", py::arithmetic());
  for (int t = 0; t <= (int)BinaryOpType::undefined; t++)
    bin.value(binary_op_type_name(BinaryOpType(t)).c_str(), BinaryOpType(t));
  bin.export_values();
  m.def("make_binary_op_expr",
        Expr::make<BinaryOpExpression, const BinaryOpType &, const Expr &,
                   const Expr &>);

  auto &&unary = py::enum_<UnaryOpType>(m, "UnaryOpType", py::arithmetic());
  for (int t = 0; t <= (int)UnaryOpType::undefined; t++)
    unary.value(unary_op_type_name(UnaryOpType(t)).c_str(), UnaryOpType(t));
  unary.export_values();
  m.def("make_unary_op_expr",
        Expr::make<UnaryOpExpression, const UnaryOpType &, const Expr &>);
#define PER_TYPE(x)                                                  \
  m.attr(("DataType_" + data_type_name(PrimitiveType::x)).c_str()) = \
      PrimitiveType::x;
#include "taichi/inc/data_type.inc.h"
#undef PER_TYPE

  m.def("data_type_size", data_type_size);
  m.def("is_quant", is_quant);
  m.def("is_integral", is_integral);
  m.def("is_signed", is_signed);
  m.def("is_real", is_real);
  m.def("is_unsigned", is_unsigned);
  m.def("is_tensor", is_tensor);

  m.def("data_type_name", data_type_name);

  m.def(
      "subscript_with_multiple_indices",
      Expr::make<IndexExpression, const Expr &, const std::vector<ExprGroup> &,
                 const std::vector<int> &, const DebugInfo &>);

  m.def("get_external_tensor_element_dim", [](const Expr &expr) {
    TI_ASSERT(expr.is<ExternalTensorExpression>());
    // FIXME: no need to make it negative since we don't support SOA
    auto dtype = expr.cast<ExternalTensorExpression>()->dt;
    return dtype->is<TensorType>()
               ? -dtype->cast<TensorType>()->get_shape().size()
               : 0;
  });

  m.def("get_external_tensor_element_type", [](const Expr &expr) {
    TI_ASSERT(expr.is<ExternalTensorExpression>());
    auto external_tensor_expr = expr.cast<ExternalTensorExpression>();
    return external_tensor_expr->dt;
  });

  m.def("get_external_tensor_element_shape", [](const Expr &expr) {
    TI_ASSERT(expr.is<ExternalTensorExpression>());
    auto external_tensor_expr = expr.cast<ExternalTensorExpression>();
    return external_tensor_expr->dt.get_shape();
  });

  m.def("get_external_tensor_dim", [](const Expr &expr) {
    TI_ASSERT(expr.is<ExternalTensorExpression>());
    return expr.cast<ExternalTensorExpression>()->ndim;
  });

  m.def("get_external_tensor_shape_along_axis",
        Expr::make<ExternalTensorShapeAlongAxisExpression, const Expr &, int,
                   const DebugInfo &>);

  m.def("get_commit_hash", get_commit_hash);
  m.def("get_version_string", get_version_string);
  m.def("get_version_major", get_version_major);
  m.def("get_version_minor", get_version_minor);
  m.def("get_version_patch", get_version_patch);
  m.def("is_extension_supported", is_extension_supported);

  // Type system

  py::class_<Type>(m, "Type").def("to_string", &Type::to_string);

  m.def("promoted_type", promoted_type);

  // Note that it is important to specify py::return_value_policy::reference for
  // the factory methods, otherwise pybind11 will delete the Types owned by
  // TypeFactory on Python-scope pointer destruction.
  py::class_<TypeFactory>(m, "TypeFactory")
      .def(
          "get_tensor_type",
          [&](TypeFactory *factory, std::vector<int> shape,
              const DataType &element_type) {
            return factory->create_tensor_type(shape, element_type);
          },
          py::return_value_policy::reference)
      .def(
          "get_struct_type",
          [&](TypeFactory *factory,
              std::vector<std::pair<DataType, std::string>> elements) {
            std::vector<AbstractDictionaryMember> members;
            for (auto &[type, name] : elements) {
              members.push_back({type, name});
            }
            return DataType(factory->get_struct_type(members));
          },
          py::return_value_policy::reference)
      .def("get_ndarray_struct_type", &TypeFactory::get_ndarray_struct_type,
           py::arg("dt"), py::arg("ndim"), py::arg("needs_grad"),
           py::return_value_policy::reference);

  m.def("get_type_factory_instance", TypeFactory::get_instance,
        py::return_value_policy::reference);

  auto operationClass = py::class_<Operation>(m, "Operation");
  auto internalOpClass = py::class_<InternalOp>(m, "InternalOp");

#define PER_INTERNAL_OP(x)                                           \
  internalOpClass.def_property_readonly_static(                      \
      #x, [](py::object) { return Operations::get(InternalOp::x); }, \
      py::return_value_policy::reference);
#include "taichi/inc/internal_ops.inc.h"
#undef PER_INTERNAL_OP
}

}  // namespace taichi
