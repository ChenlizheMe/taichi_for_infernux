# Modified by Infernux in 2026: private compiler-relative imports.
import numbers
from types import FunctionType, MethodType
from typing import Any, Iterable

import numpy as np
from .._lib import core as _ti_core
from ._ndrange import GroupedNDRange, _Ndrange
from .any_array import AnyArray
from .exception import (
    TaichiCompilationError,
    TaichiRuntimeError,
    TaichiSyntaxError,
    TaichiTypeError,
)
from .expr import Expr, make_expr_group
from .matrix import (
    Matrix,
    MatrixType,
    Vector,
    make_matrix,
)
from .struct import Struct
from .util import (
    cook_dtype,
    is_taichi_class,
    python_scope,
    taichi_scope,
    warning,
)
from ..types.primitive_types import (
    all_types,
    f16,
    f32,
    f64,
    i32,
    i64,
    u8,
    u32,
    u64,
)


class _UnsupportedCompilerFeature:
    """Sentinel for Taichi runtime features excluded from Infernux kernels."""

    def __init__(self, *args, **kwargs):
        raise TaichiRuntimeError("Infernux GPU kernels use inx.buffer; Taichi fields are not supported")


SharedArray = _UnsupportedCompilerFeature
MeshElementFieldProxy = _UnsupportedCompilerFeature
MeshInstance = _UnsupportedCompilerFeature
MeshRelationAccessProxy = _UnsupportedCompilerFeature
MeshReorderedMatrixFieldProxy = _UnsupportedCompilerFeature
MeshReorderedScalarFieldProxy = _UnsupportedCompilerFeature


@taichi_scope
def expr_init_shared_array(shape, element_type):
    return (
        get_runtime()
        .compiling_callable.ast_builder()
        .expr_alloca_shared_array(shape, element_type, _ti_core.DebugInfo(get_runtime().get_current_src_info()))
    )


@taichi_scope
def expr_init(rhs):
    if rhs is None:
        return Expr(
            get_runtime()
            .compiling_callable.ast_builder()
            .expr_alloca(_ti_core.DebugInfo(get_runtime().get_current_src_info()))
        )
    if isinstance(rhs, Matrix) and (hasattr(rhs, "_DIM")):
        return Matrix(*rhs.to_list(), ndim=rhs.ndim)
    if isinstance(rhs, Matrix):
        return make_matrix(rhs.to_list())
    if isinstance(rhs, SharedArray):
        return rhs
    if isinstance(rhs, Struct):
        return Struct(rhs.to_dict(include_methods=True, include_ndim=True))
    if isinstance(rhs, list):
        return [expr_init(e) for e in rhs]
    if isinstance(rhs, tuple):
        return tuple(expr_init(e) for e in rhs)
    if isinstance(rhs, dict):
        return dict((key, expr_init(val)) for key, val in rhs.items())
    if isinstance(rhs, _ti_core.DataType):
        return rhs
    if isinstance(rhs, _ti_core.Arch):
        return rhs
    if isinstance(rhs, _Ndrange):
        return rhs
    if isinstance(rhs, MeshElementFieldProxy):
        return rhs
    if isinstance(rhs, MeshRelationAccessProxy):
        return rhs
    if hasattr(rhs, "_data_oriented"):
        return rhs
    return Expr(
        get_runtime()
        .compiling_callable.ast_builder()
        .expr_var(Expr(rhs).ptr, _ti_core.DebugInfo(get_runtime().get_current_src_info()))
    )


def begin_frontend_struct_for(ast_builder, group, loop_range):
    if not isinstance(loop_range, AnyArray):
        raise TypeError(
            f"Cannot lower a buffer loop over {type(loop_range)}; an external buffer expression is required."
        )
    if group.size() != len(loop_range.shape):
        raise IndexError(
            "Number of struct-for indices does not match loop variable dimensionality "
            f"({group.size()} != {len(loop_range.shape)}). Maybe you wanted to "
            'use "for I in ti.grouped(x)" to group all indices into a single vector I?'
        )
    dbg_info = _ti_core.DebugInfo(get_runtime().get_current_src_info())
    ast_builder.begin_frontend_struct_for_on_external_tensor(group, loop_range._loop_range(), dbg_info)


def begin_frontend_if(ast_builder, cond, stmt_dbg_info):
    assert ast_builder is not None
    if is_taichi_class(cond):
        raise ValueError(
            "The truth value of vectors/matrices is ambiguous.\n"
            "Consider using `any` or `all` when comparing vectors/matrices:\n"
            "    if all(x == y):\n"
            "or\n"
            "    if any(x != y):\n"
        )
    ast_builder.begin_frontend_if(Expr(cond).ptr, stmt_dbg_info)


@taichi_scope
def _calc_slice(index, default_stop):
    start, stop, step = index.start or 0, index.stop or default_stop, index.step or 1

    def check_validity(x):
        #  TODO(mzmzm): support variable in slice
        if isinstance(x, Expr):
            raise TaichiCompilationError(
                "Taichi does not support variables in slice now, please use constant instead of it."
            )

    check_validity(start), check_validity(stop), check_validity(step)
    return [_ for _ in range(start, stop, step)]


def validate_subscript_index(value, index):
    if isinstance(index, Expr):
        return

    if isinstance(index, Iterable):
        for ind in index:
            validate_subscript_index(value, ind)

    if isinstance(index, slice):
        validate_subscript_index(value, index.start)
        validate_subscript_index(value, index.stop)

    if isinstance(index, numbers.Number) and index < 0:
        raise TaichiSyntaxError("Negative indices are not supported in Taichi kernels.")


@taichi_scope
def subscript(ast_builder, value, *_indices, skip_reordered=False):
    dbg_info = _ti_core.DebugInfo(get_runtime().get_current_src_info())
    ast_builder = get_runtime().compiling_callable.ast_builder()
    # Directly evaluate in Python for non-Taichi types
    if not isinstance(
        value,
        (
            Expr,
            AnyArray,
            MeshElementFieldProxy,
            MeshRelationAccessProxy,
            SharedArray,
        ),
    ):
        if len(_indices) == 1:
            _indices = _indices[0]
        return value.__getitem__(_indices)

    has_slice = False

    flattened_indices = []
    for _index in _indices:
        if isinstance(_index, Matrix):
            ind = _index.to_list()
        elif isinstance(_index, slice):
            ind = [_index]
            has_slice = True
        else:
            ind = [_index]
        flattened_indices += ind
    indices = tuple(flattened_indices)
    validate_subscript_index(value, indices)

    if len(indices) == 1 and indices[0] is None:
        indices = ()

    if has_slice:
        if not (isinstance(value, Expr) and value.is_tensor()):
            raise TaichiSyntaxError(f"The type {type(value)} do not support index of slice type")
    else:
        indices_expr_group = make_expr_group(*indices)

    if isinstance(value, SharedArray):
        return value.subscript(*indices)
    if isinstance(value, MeshElementFieldProxy):
        return value.subscript(*indices)
    if isinstance(value, MeshRelationAccessProxy):
        return value.subscript(*indices)
    if isinstance(value, (MeshReorderedScalarFieldProxy, MeshReorderedMatrixFieldProxy)) and not skip_reordered:
        reordered_index = tuple(
            [
                Expr(
                    ast_builder.mesh_index_conversion(
                        value.mesh_ptr, value.element_type, Expr(indices[0]).ptr, ConvType.g2r, dbg_info
                    )
                )
            ]
        )
        return subscript(ast_builder, value, *reordered_index, skip_reordered=True)
    if isinstance(value, AnyArray):
        return Expr(ast_builder.expr_subscript(value.ptr, indices_expr_group, dbg_info))
    assert isinstance(value, Expr)
    # Index into TensorType
    # value: IndexExpression with ret_type = TensorType
    assert value.is_tensor()

    if has_slice:
        shape = value.get_shape()
        dim = len(shape)
        assert dim == len(indices)
        indices = [
            _calc_slice(index, shape[i]) if isinstance(index, slice) else index for i, index in enumerate(indices)
        ]
        if dim == 1:
            assert isinstance(indices[0], list)
            multiple_indices = [make_expr_group(i) for i in indices[0]]
            return_shape = (len(indices[0]),)
        else:
            assert dim == 2
            if isinstance(indices[0], list) and isinstance(indices[1], list):
                multiple_indices = [make_expr_group(i, j) for i in indices[0] for j in indices[1]]
                return_shape = (len(indices[0]), len(indices[1]))
            elif isinstance(indices[0], list):  # indices[1] is not list
                multiple_indices = [make_expr_group(i, indices[1]) for i in indices[0]]
                return_shape = (len(indices[0]),)
            else:  # indices[0] is not list while indices[1] is list
                multiple_indices = [make_expr_group(indices[0], j) for j in indices[1]]
                return_shape = (len(indices[1]),)
        return Expr(
            _ti_core.subscript_with_multiple_indices(
                value.ptr,
                multiple_indices,
                return_shape,
                dbg_info,
            )
        )
    return Expr(ast_builder.expr_subscript(value.ptr, indices_expr_group, dbg_info))


class SrcInfoGuard:
    def __init__(self, info_stack, info):
        self.info_stack = info_stack
        self.info = info

    def __enter__(self):
        self.info_stack.append(self.info)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.info_stack.pop()


class PyTaichi:
    def __init__(self):
        self.prog = None
        # Infernux owns compiler initialization and does not call Taichi's
        # public ``ti.init`` path.  Keep the AST semantics required by the
        # private Python-to-SPIR-V frontend on the compiler runtime itself.
        self.short_circuit_operators = True
        self.print_full_traceback = False
        self.unrolling_limit = 32
        self.src_info_stack = []
        self.inside_kernel = False
        self.compiling_callable = None  # pointer to instance of lang::Kernel/Function
        self.current_kernel = None
        self.default_fp = f32
        self.default_ip = i32
        self.default_up = u32

    def src_info_guard(self, info):
        return SrcInfoGuard(self.src_info_stack, info)

    def get_current_src_info(self):
        return self.src_info_stack[-1]

    def set_default_fp(self, fp):
        assert fp in [f16, f32, f64]
        self.default_fp = fp
        default_cfg().default_fp = self.default_fp

    def set_default_ip(self, ip):
        assert ip in [i32, i64]
        self.default_ip = ip
        self.default_up = u32 if ip == i32 else u64
        default_cfg().default_ip = self.default_ip
        default_cfg().default_up = self.default_up

    def create_program(self):
        if self.prog is None:
            self.prog = _ti_core.Program()

pytaichi = PyTaichi()


def get_runtime():
    return pytaichi


@taichi_scope
def static_print(*args, __p=print, **kwargs):
    """The print function in Taichi scope.

    This function is called at compile time and has no runtime overhead.
    """
    __p(*args, **kwargs)


# we don't add @taichi_scope decorator for @ti.pyfunc to work
def static_assert(cond, msg=None):
    """Throw AssertionError when `cond` is False.

    This function is called at compile time and has no runtime overhead.
    The bool value in `cond` must can be determined at compile time.

    Args:
        cond (bool): an expression with a bool value.
        msg (str): assertion message.

    Example::

        >>> year = 2001
        >>> @ti.kernel
        >>> def test():
        >>>     ti.static_assert(year % 4 == 0, "the year must be a lunar year")
        AssertionError: the year must be a lunar year
    """
    if isinstance(cond, Expr):
        raise TaichiTypeError("Static assert with non-static condition")
    if msg is not None:
        assert cond, msg
    else:
        assert cond


def inside_kernel():
    return pytaichi.inside_kernel


@taichi_scope
def ti_format_list_to_content_entries(raw):
    # return a pair of [content, format]
    def entry2content(_var):
        if isinstance(_var, str):
            return [_var, None]
        if isinstance(_var, list):
            assert len(_var) == 2 and (isinstance(_var[1], str) or _var[1] is None)
            _var[0] = Expr(_var[0]).ptr
            return _var
        return [Expr(_var).ptr, None]

    def list_ti_repr(_var):
        yield "["  # distinguishing tuple & list will increase maintenance cost
        for i, v in enumerate(_var):
            if i:
                yield ", "
            yield v
        yield "]"

    def vars2entries(_vars):
        for _var in _vars:
            # If the first element is '__ti_fmt_value__', this list is an Expr and its format.
            if isinstance(_var, list) and len(_var) == 3 and isinstance(_var[0], str) and _var[0] == "__ti_fmt_value__":
                # yield [Expr, format] as a whole and don't pass it to vars2entries() again
                yield _var[1:]
                continue
            elif hasattr(_var, "__ti_repr__"):
                res = _var.__ti_repr__()
            elif isinstance(_var, (list, tuple)):
                # If the first element is '__ti_format__', this list is the result of ti_format.
                if len(_var) > 0 and isinstance(_var[0], str) and _var[0] == "__ti_format__":
                    res = _var[1:]
                else:
                    res = list_ti_repr(_var)
            else:
                yield _var
                continue

            for v in vars2entries(res):
                yield v

    def fused_string(entries):
        accumated = ""
        for entry in entries:
            if isinstance(entry, str):
                accumated += entry
            else:
                if accumated:
                    yield accumated
                    accumated = ""
                yield entry
        if accumated:
            yield accumated

    def extract_formats(entries):
        contents, formats = zip(*entries)
        return list(contents), list(formats)

    entries = vars2entries(raw)
    entries = fused_string(entries)
    entries = [entry2content(entry) for entry in entries]
    return extract_formats(entries)


@taichi_scope
def ti_print(*_vars, sep=" ", end="\n"):
    def add_separators(_vars):
        for i, _var in enumerate(_vars):
            if i:
                yield sep
            yield _var
        yield end

    _vars = add_separators(_vars)
    contents, formats = ti_format_list_to_content_entries(_vars)
    get_runtime().compiling_callable.ast_builder().create_print(
        contents, formats, _ti_core.DebugInfo(get_runtime().get_current_src_info())
    )


@taichi_scope
def ti_format(*args):
    content = args[0]
    mixed = args[1:]
    new_mixed = []
    args = []
    for x in mixed:
        # x is a (formatted) Expr
        if isinstance(x, Expr) or (isinstance(x, list) and len(x) == 3 and x[0] == "__ti_fmt_value__"):
            new_mixed.append("{}")
            args.append(x)
        else:
            new_mixed.append(x)
    content = content.format(*new_mixed)
    res = content.split("{}")
    assert len(res) == len(args) + 1, "Number of args is different from number of positions provided in string"

    for i, arg in enumerate(args):
        res.insert(i * 2 + 1, arg)
    res.insert(0, "__ti_format__")
    return res


@taichi_scope
def ti_assert(cond, msg, extra_args, dbg_info):
    # Mostly a wrapper to help us convert from Expr (defined in Python) to
    # _ti_core.Expr (defined in C++)
    get_runtime().compiling_callable.ast_builder().create_assert_stmt(Expr(cond).ptr, msg, extra_args, dbg_info)


@taichi_scope
def ti_int(_var):
    if hasattr(_var, "__ti_int__"):
        return _var.__ti_int__()
    return int(_var)


@taichi_scope
def ti_bool(_var):
    if hasattr(_var, "__ti_bool__"):
        return _var.__ti_bool__()
    return bool(_var)


@taichi_scope
def ti_float(_var):
    if hasattr(_var, "__ti_float__"):
        return _var.__ti_float__()
    return float(_var)


@taichi_scope
def zero(x):
    # TODO: get dtype from Expr and Matrix:
    """Returns an array of zeros with the same shape and type as the input. It's also a scalar
    if the input is a scalar.

    Args:
        x (Union[:mod:`~taichi.types.primitive_types`, :class:`~taichi.Matrix`]): The input.

    Returns:
        A new copy of the input but filled with zeros.

    Example::

        >>> x = ti.Vector([1, 1])
        >>> @ti.kernel
        >>> def test():
        >>>     y = ti.zero(x)
        >>>     print(y)
        [0, 0]
    """
    return x * 0


@taichi_scope
def one(x):
    """Returns an array of ones with the same shape and type as the input. It's also a scalar
    if the input is a scalar.

    Args:
        x (Union[:mod:`~taichi.types.primitive_types`, :class:`~taichi.Matrix`]): The input.

    Returns:
        A new copy of the input but filled with ones.

    Example::

        >>> x = ti.Vector([0, 0])
        >>> @ti.kernel
        >>> def test():
        >>>     y = ti.one(x)
        >>>     print(y)
        [1, 1]
    """
    return zero(x) + 1


def static(x, *xs) -> Any:
    """Evaluates a Taichi-scope expression at compile time.

    `static()` is what enables the so-called metaprogramming in Taichi. It is
    in many ways similar to ``constexpr`` in C++.

    See also https://docs.taichi-lang.org/docs/meta.

    Args:
        x (Any): an expression to be evaluated
        *xs (Any): for Python-ish swapping assignment

    Example:
        The most common usage of `static()` is for compile-time evaluation::

            >>> cond = False
            >>>
            >>> @ti.kernel
            >>> def run():
            >>>     if ti.static(cond):
            >>>         do_a()
            >>>     else:
            >>>         do_b()

        Depending on the value of ``cond``, ``run()`` will be directly compiled
        into either ``do_a()`` or ``do_b()``. Thus there won't be a runtime
        condition check.

        Another common usage is for compile-time loop unrolling::

            >>> @ti.kernel
            >>> def run():
            >>>     for i in ti.static(range(3)):
            >>>         print(i)
            >>>
            >>> # The above will be unrolled to:
            >>> @ti.kernel
            >>> def run():
            >>>     print(0)
            >>>     print(1)
            >>>     print(2)
    """
    if len(xs):  # for python-ish pointer assign: x, y = ti.static(y, x)
        return [static(x)] + [static(x) for x in xs]

    if (
        isinstance(
            x,
            (
                bool,
                int,
                float,
                range,
                list,
                tuple,
                enumerate,
                GroupedNDRange,
                _Ndrange,
                zip,
                filter,
                map,
            ),
        )
        or x is None
    ):
        return x
    if isinstance(x, (np.bool_, np.integer, np.floating)):
        return x

    if isinstance(x, AnyArray):
        return x
    if isinstance(x, (FunctionType, MethodType)):
        return x
    raise ValueError(f"Input to ti.static must be compile-time constants or global pointers, instead of {type(x)}")


@taichi_scope
def grouped(x):
    """Groups the indices in the iterator returned by `ndrange()` into a 1-D vector.

    This is often used when you want to iterate over all indices returned by `ndrange()`
    in one `for` loop and a single index.

    Args:
        x (:func:`~taichi.ndrange`): an iterator object returned by `ti.ndrange`.

    Example::
        >>> # without ti.grouped
        >>> for I in ti.ndrange(2, 3):
        >>>     print(I)
        prints 0, 1, 2, 3, 4, 5

        >>> # with ti.grouped
        >>> for I in ti.grouped(ti.ndrange(2, 3)):
        >>>     print(I)
        prints [0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]
    """
    if isinstance(x, _Ndrange):
        return x.grouped()
    return x


def current_cfg():
    return get_runtime().prog.config()


def default_cfg():
    return _ti_core.default_compile_config()


def call_internal(name, *args, with_runtime_context=True):
    return expr_init(_ti_core.insert_internal_func_call(getattr(_ti_core.InternalOp, name), make_expr_group(args)))


def get_cuda_compute_capability():
    return _ti_core.query_int64("cuda_compute_capability")


@taichi_scope
def mesh_relation_access(mesh, from_index, to_element_type):
    # to support ti.mesh_local and access mesh attribute as field
    if isinstance(from_index, MeshInstance):
        return getattr(from_index, element_type_name(to_element_type))
    if isinstance(mesh, MeshInstance):
        return MeshRelationAccessProxy(mesh, from_index, to_element_type)
    raise RuntimeError("Relation access should be with a mesh instance!")


__all__ = [
    "grouped",
    "one",
    "static",
    "static_assert",
    "static_print",
    "zero",
]
