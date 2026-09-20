"""Compile from the staged private frontend without an engine or GPU device.

Pass the installed Infernux/_compiler/taichi/_vendor/taichi directory.
"""

from pathlib import Path
import gc
import importlib.util
import importlib.machinery
import sys
import types
import weakref

frontend = Path(sys.argv[1]).resolve(strict=True)
namespace = "Infernux._compiler.taichi._vendor.taichi"
parts = namespace.split(".")
for length in range(1, len(parts)):
    name = ".".join(parts[:length])
    package = types.ModuleType(name)
    package.__path__ = []
    sys.modules[name] = package

spec = importlib.machinery.PathFinder.find_spec(
    namespace + "._lib.core._infernux_gpu_compiler", [str(frontend / "_lib/core")]
)
assert spec is not None, "Staged native compiler is missing"
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
assert native.__name__.endswith("._infernux_gpu_compiler")
for name in (
    "SNodeType", "SNodeGradType", "SNodeAccessFlag", "Format", "TextureOpType",
    "AutodiffMode", "make_external_tensor_grad_expr", "get_external_tensor_needs_grad",
    "make_texture_ptr_expr", "make_rw_texture_ptr_expr", "set_lib_dir",
    "make_global_load_stmt", "make_global_store_stmt", "make_frontend_assign_stmt",
):
    assert not hasattr(native, name), f"Retired runtime binding remains: {name}"
for name in (
    "stop_grad", "insert_deactivate", "insert_activate", "expr_snode_get_addr",
    "expr_snode_append", "expr_snode_is_active", "expr_snode_length",
    "insert_external_func_call", "begin_frontend_struct_for_on_snode",
    "begin_frontend_mesh_for", "end_frontend_mesh_for", "mesh_index_conversion",
    "insert_patch_idx_expr", "make_texture_op_expr", "sifakis_svd_f32",
    "sifakis_svd_f64", "bit_vectorize", "parallelize", "insert_snode_access_flag",
    "reset_snode_access_flag",
):
    assert not hasattr(native.ASTBuilder, name), f"Retired AST binding remains: {name}"
spec = importlib.util.spec_from_file_location(
    namespace, frontend / "__init__.py", submodule_search_locations=[str(frontend)]
)
ti = importlib.util.module_from_spec(spec)
sys.modules[namespace] = ti
spec.loader.exec_module(ti)
impl = ti.lang.impl
for name in (
    "MeshInstance", "MeshElementFieldProxy", "MeshRelationAccessProxy",
    "MeshReorderedMatrixFieldProxy", "MeshReorderedScalarFieldProxy",
    "mesh_relation_access", "get_cuda_compute_capability",
):
    assert not hasattr(impl, name), f"Retired compiler branch remains: {name}"
runtime = impl.get_runtime()
runtime.create_program()
assert runtime.prog.config().arch == ti.vulkan
assert not hasattr(native, "default_compile_config")
assert not hasattr(native, "reset_default_compile_config")
assert not hasattr(runtime.prog.config(), "use_llvm")
assert not hasattr(runtime.prog.config(), "device_memory_GB")
# Local option changes cannot contaminate future compilation contexts.
first_configuration = runtime.prog.config()
first_configuration.fast_math = False
fresh_program = native.Program()
assert fresh_program.config().fast_math is True
assert fresh_program.config().print_ir_dbg_info is False
assert first_configuration.fast_math is False
del first_configuration, fresh_program
buffer_description = ti.types.external_buffer(dtype=ti.i32, ndim=1)


@ti.lang.kernel_impl.func
def typed_pair(value: ti.i32) -> tuple[ti.i32, ti.i32]:
    return value * 5, 7


@ti.kernel
def affine(values: buffer_description):
    for i in range(values.shape[0]):
        first, second = typed_pair(i)
        values[i] = first + second


key = affine.ensure_compiled(buffer_description)
kernel = affine.compiled_kernels[key]
program = runtime.prog
compiled = program.compile_kernel(program.config(), program.get_device_caps(), kernel)
assert compiled._infernux_spirv_tasks
assert compiled._infernux_task_metadata
assert all(task["threads_per_group"] > 0 for task in compiled._infernux_task_metadata)
assert all(task["entry_point"] == task["name"] for task in compiled._infernux_task_metadata)
assert all(tuple(task["workgroup_size"]) == (task["threads_per_group"], 1, 1)
           for task in compiled._infernux_task_metadata)
assert compiled._infernux_required_capabilities == {"spirv_version": 0x10300}

# Buffer iteration must reach its actual lowering, not an absent MeshTaichi
# compatibility object. It remains compiler-only and does not allocate data.
@ti.kernel
def buffer_loop(values: buffer_description):
    for i in values:
        values[i] = i + 2


loop_key = buffer_loop.ensure_compiled(buffer_description)
loop_ir = buffer_loop.compiled_kernels[loop_key]
loop_compiled = program.compile_kernel(program.config(), program.get_device_caps(), loop_ir)
assert loop_compiled._infernux_spirv_tasks
del buffer_loop, loop_ir


def loop_count(artifact):
    import struct
    count = 0
    for task in artifact._infernux_spirv_tasks:
        words = struct.unpack(f"<{len(task) // 4}I", task)
        offset = 5
        while offset < len(words):
            size = words[offset] >> 16
            assert size > 0
            count += (words[offset] & 0xffff) == 246  # OpLoopMerge
            offset += size
        assert offset == len(words)
    return count


@ti.kernel
def short_serial_loop(values: buffer_description):
    for i in range(values.shape[0]):
        total = values[i]
        for j in range(3):
            total = total * 7 + j
        values[i] = total


@ti.kernel
def large_serial_loop(values: buffer_description):
    for i in range(values.shape[0]):
        total = values[i]
        for j in range(64):
            total = total * 7 + j
        values[i] = total


short_key = short_serial_loop.ensure_compiled(buffer_description)
short_artifact = program.compile_kernel(
    program.config(), program.get_device_caps(), short_serial_loop.compiled_kernels[short_key])
large_key = large_serial_loop.ensure_compiled(buffer_description)
large_artifact = program.compile_kernel(
    program.config(), program.get_device_caps(), large_serial_loop.compiled_kernels[large_key])
# The compiler-generated outer grid-stride loop remains in both; only the
# short serial loop is unfolded. Do not expand large loops into giant shaders.
assert loop_count(short_artifact) == 1
assert loop_count(large_artifact) == 2
del short_serial_loop, large_serial_loop
assert not hasattr(runtime, 'kernels')
assert not hasattr(affine, "grad")
assert "Infernux.lib" not in sys.modules
assert "taichi" not in sys.modules

# A kernel owns its native IR and keeps its Program alive, not the reverse.
# Exported SPIR-V is a value and remains usable after both have been released.
program_reference = weakref.ref(program)
kernel_reference = weakref.ref(kernel)
runtime.prog = None
del program
gc.collect()
assert program_reference() is not None, 'Kernel lost its compiler context'
del affine, kernel
gc.collect()
assert kernel_reference() is None
assert program_reference() is None, 'Compiler context retained after its final kernel'
assert compiled._infernux_spirv_tasks

# Repeated fresh lowering must not retain prior Python wrappers/native IR.
# This intentionally bypasses the engine artifact cache.
runtime.create_program()


def churn(values: buffer_description):
    for i in range(values.shape[0]):
        values[i] = i * 3 + 1


def invalid(values: buffer_description):
    for i in range(values.shape[0]):
        values[i] = undefined_compiler_value


for iteration in range(32):
    request = ti.kernel(churn)
    key = request.ensure_compiled(buffer_description)
    ir = request.compiled_kernels[key]
    compiled = runtime.prog.compile_kernel(runtime.prog.config(), runtime.prog.get_device_caps(), ir)
    references = weakref.ref(request), weakref.ref(ir)
    assert compiled._infernux_spirv_tasks
    del request, ir, key
    gc.collect()
    assert all(reference() is None for reference in references), iteration

    request = ti.kernel(invalid)
    reference = weakref.ref(request)
    try:
        request.ensure_compiled(buffer_description)
    except Exception as error:
        assert 'undefined_compiler_value' in str(error), error
    else:
        raise AssertionError('Invalid kernel unexpectedly compiled')
    assert runtime.inside_kernel is False
    assert runtime.current_kernel is None
    assert runtime.compiling_callable is None
    assert request.kernel_cpp is None
    del request
    gc.collect()
    assert reference() is None, 'Failed compilation retained its request'

# A caller may keep a compiler error (and its traceback) for diagnostics. Any
# native AST handles referenced by that traceback must retain their context.
request = ti.kernel(invalid)
program_reference = weakref.ref(runtime.prog)
retained_error = None
try:
    request.ensure_compiled(buffer_description)
except Exception as error:
    retained_error = error
assert retained_error is not None
runtime.prog = None
gc.collect()
assert program_reference() is not None, 'Failure traceback lost its native compiler owner'
retained_error = None
del request
gc.collect()
assert program_reference() is None, 'Discarded failure still retains its compiler owner'

# Borrowed configuration/builders must keep their actual native owners alive.
runtime.create_program()
request = ti.kernel(churn)
key = request.ensure_compiled(buffer_description)
ir = request.compiled_kernels[key]
builder = ir.ast_builder()
configuration_view = runtime.prog.config()
kernel_reference = weakref.ref(ir)
program_reference = weakref.ref(runtime.prog)
runtime.prog = None
del request, ir, key
gc.collect()
assert kernel_reference() is not None, 'AST builder lost its native kernel owner'
del builder
gc.collect()
assert kernel_reference() is None
assert program_reference() is not None, 'Configuration view lost its native owner'
del configuration_view
gc.collect()
assert program_reference() is None
assert not hasattr(ti.lang.kernel_impl, 'real_func')
for name in ('Function', 'FunctionKey', 'get_external_tensor_real_func_args'):
    assert not hasattr(native, name), f'Unused standalone-function export: {name}'
assert not hasattr(native.ASTBuilder, 'insert_func_call')

# Compiler contexts are ordinary owners, not an exclusive process runtime.
# Keep IR from the first context while compiling/releasing a second context,
# then compile the retained IR again. This is serial lifetime isolation, not
# a claim that shared frontend/type-factory state supports parallel threads.
first_program = native.Program()
second_program = native.Program()
runtime.prog = first_program
first_request = ti.kernel(churn)
first_key = first_request.ensure_compiled(buffer_description)
first_ir = first_request.compiled_kernels[first_key]
first_compiled = first_program.compile_kernel(
    first_program.config(), first_program.get_device_caps(), first_ir)
runtime.prog = second_program
second_request = ti.kernel(churn)
second_key = second_request.ensure_compiled(buffer_description)
second_ir = second_request.compiled_kernels[second_key]
second_compiled = second_program.compile_kernel(
    second_program.config(), second_program.get_device_caps(), second_ir)
assert first_compiled._infernux_spirv_tasks
assert second_compiled._infernux_spirv_tasks
second_reference = weakref.ref(second_program)
runtime.prog = first_program
del second_program, second_request, second_ir
gc.collect()
assert second_reference() is None
first_again = first_program.compile_kernel(
    first_program.config(), first_program.get_device_caps(), first_ir)
assert first_again._infernux_spirv_tasks == first_compiled._infernux_spirv_tasks
assert first_again._infernux_task_metadata == first_compiled._infernux_task_metadata
first_reference = weakref.ref(first_program)
runtime.prog = None
del first_program, first_request, first_ir
gc.collect()
assert first_reference() is None
assert second_compiled._infernux_spirv_tasks
print("INFERNUX_COMPILER_ONLY_SPIRV_OK", flush=True)
