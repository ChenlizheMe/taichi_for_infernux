# Modified by Infernux in 2026: metadata-only kernel compilation for engine buffers.
import ast
import functools
import inspect
import textwrap
import typing
import weakref

from Infernux._compiler.taichi._vendor import taichi
from .._lib import core as _ti_core
from . import impl
from .any_array import AnyArray
from ._wrap_inspect import getsourcefile, getsourcelines
from .ast import (
    ASTTransformerContext,
    transform_tree,
)
from .ast.ast_transformer_utils import ReturnStatus
from .exception import (
    TaichiRuntimeError,
    TaichiRuntimeTypeError,
    TaichiSyntaxError,
    TaichiTypeError,
)
from .kernel_arguments import KernelArgument
from .matrix import MatrixType
from .struct import StructType
from ..types import (
    buffer_type,
    primitive_types,
    template,
)

from .. import _logging


def func(fn):
    """Inline a numerical helper into the current kernel's AST."""
    fun = Func(fn)

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        return fun(*args, **kwargs)

    decorated._is_taichi_function = True
    decorated.func = fun
    return decorated


def pyfunc(fn):
    """Evaluate shared numeric helpers on literals or lower them in kernel scope."""
    compiled = Func(fn)

    @functools.wraps(fn)
    def decorated(*args, **kwargs):
        if impl.inside_kernel():
            return compiled(*args, **kwargs)
        return fn(*args, **kwargs)

    decorated._is_taichi_function = True
    decorated.func = compiled
    return decorated




def _get_tree_and_ctx(
    self,
    excluded_parameters=(),
    is_kernel=True,
    arg_features=None,
    args=None,
    ast_builder=None,
):
    file = getsourcefile(self.func)
    src, start_lineno = getsourcelines(self.func)
    src = [textwrap.fill(line, tabsize=4, width=9999) for line in src]
    tree = ast.parse(textwrap.dedent("\n".join(src)))

    func_body = tree.body[0]
    func_body.decorator_list = []

    global_vars = _get_global_vars(self.func)

    if is_kernel:
        # inject template parameters into globals
        for i in self.template_slot_locations:
            template_var_name = self.arguments[i].name
            global_vars[template_var_name] = args[i]

    return tree, ASTTransformerContext(
        excluded_parameters=excluded_parameters,
        is_kernel=is_kernel,
        func=self,
        arg_features=arg_features,
        global_vars=global_vars,
        argument_data=args,
        src=src,
        start_lineno=start_lineno,
        file=file,
        ast_builder=ast_builder,
    )


def _process_args(self, args, kwargs):
    ret = [argument.default for argument in self.arguments]
    len_args = len(args)

    if len_args > len(ret):
        arg_str = ", ".join([str(arg) for arg in args])
        expected_str = ", ".join([f"{arg.name} : {arg.annotation}" for arg in self.arguments])
        msg = f"Too many arguments. Expected ({expected_str}), got ({arg_str})."
        raise TaichiSyntaxError(msg)

    for i, arg in enumerate(args):
        ret[i] = arg

    for key, value in kwargs.items():
        found = False
        for i, arg in enumerate(self.arguments):
            if key == arg.name:
                if i < len_args:
                    raise TaichiSyntaxError(f"Multiple values for argument '{key}'.")
                ret[i] = value
                found = True
                break
        if not found:
            raise TaichiSyntaxError(f"Unexpected argument '{key}'.")

    for i, arg in enumerate(ret):
        if arg is inspect.Parameter.empty:
            if self.arguments[i].annotation is inspect._empty:
                raise TaichiSyntaxError(f"Parameter `{self.arguments[i].name}` missing.")
            else:
                raise TaichiSyntaxError(
                    f"Parameter `{self.arguments[i].name} : {self.arguments[i].annotation}` missing."
                )

    return ret


class Func:
    def __init__(self, _func):
        self.func = _func
        self.arguments = []
        self.return_type = None
        self.extract_arguments()
        self.has_print = False

    def __call__(self, *args, **kwargs):
        args = _process_args(self, args, kwargs)
        if not impl.inside_kernel():
            raise TaichiSyntaxError("Compiler helper functions cannot execute in Python-scope.")
        tree, ctx = _get_tree_and_ctx(
            self,
            is_kernel=False,
            args=args,
            ast_builder=impl.get_runtime().current_kernel.ast_builder(),
        )
        result = transform_tree(tree, ctx)
        if self.return_type and ctx.returned != ReturnStatus.ReturnedValue:
            raise TaichiSyntaxError("Function has a return type but does not have a return statement")
        return result

    def extract_arguments(self):
        sig = inspect.signature(self.func)
        if sig.return_annotation not in (inspect.Signature.empty, None):
            self.return_type = sig.return_annotation
            if typing.get_origin(self.return_type) is tuple:
                self.return_type = typing.get_args(self.return_type)
            if not isinstance(self.return_type, (list, tuple)):
                self.return_type = (self.return_type,)
            for i, return_type in enumerate(self.return_type):
                if return_type is Ellipsis:
                    raise TaichiSyntaxError("Ellipsis is not supported in return type annotations")
        params = sig.parameters
        arg_names = params.keys()
        for i, arg_name in enumerate(arg_names):
            param = params[arg_name]
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                raise TaichiSyntaxError("Taichi functions do not support variable keyword parameters (i.e., **kwargs)")
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                raise TaichiSyntaxError("Taichi functions do not support variable positional parameters (i.e., *args)")
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                raise TaichiSyntaxError("Taichi functions do not support keyword parameters")
            if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
                raise TaichiSyntaxError('Taichi functions only support "positional or keyword" parameters')
            annotation = param.annotation
            if annotation is not inspect.Parameter.empty:
                if isinstance(annotation, buffer_type.BufferType):
                    pass
                elif isinstance(annotation, MatrixType):
                    pass
                elif isinstance(annotation, StructType):
                    pass
                elif id(annotation) in primitive_types.type_ids:
                    pass
                elif isinstance(annotation, template):
                    pass
                elif isinstance(annotation, primitive_types.RefType):
                    pass
                else:
                    raise TaichiSyntaxError(f"Invalid type annotation (argument {i}) of Taichi function: {annotation}")
            self.arguments.append(KernelArgument(annotation, param.name, param.default))


class TaichiCallableTemplateMapper:
    def __init__(self, arguments, template_slot_locations):
        self.arguments = arguments
        self.num_args = len(arguments)
        self.template_slot_locations = template_slot_locations
        self.mapping = {}

    @staticmethod
    def extract_arg(arg, anno, arg_name):
        if isinstance(anno, template):
            if isinstance(arg, taichi.lang.expr.Expr):
                return arg.ptr.get_underlying_ptr_address()
            if isinstance(arg, _ti_core.Expr):
                return arg.get_underlying_ptr_address()
            if isinstance(arg, tuple):
                return tuple(TaichiCallableTemplateMapper.extract_arg(item, anno, arg_name) for item in arg)

            if isinstance(arg, (list, tuple, dict, set)):
                # [Composite arguments] Return weak reference to the object
                # Taichi kernel will cache the extracted arguments, thus we can't simply return the original argument.
                # Instead, a weak reference to the original value is returned to avoid memory leak.

                # TODO(zhanlue): replacing "tuple(args)" with "hash of argument values"
                # This can resolve the following issues:
                # 1. Invalid weak-ref will leave a dead(dangling) entry in both caches: "self.mapping" and "self.compiled_functions"
                # 2. Different argument instances with same type and same value, will get templatized into seperate kernels.
                return weakref.ref(arg)

            # [Primitive arguments] Return the value
            return arg
        if isinstance(anno, buffer_type.BufferType):
            if arg is anno:
                element_type = anno.dtype
                if isinstance(element_type, MatrixType):
                    element_type = _ti_core.get_type_factory_instance().get_tensor_type(
                        element_type.get_shape(), element_type.dtype
                    )
                return element_type, anno.ndim, False, anno.boundary
            if isinstance(arg, AnyArray):
                ty = arg.get_type()
                anno.check_matched(ty, arg_name)
                return ty.element_type, len(arg.shape), ty.needs_grad, anno.boundary
            raise TaichiRuntimeTypeError(
                f"Compiler argument {arg_name} requires its buffer type description, not runtime data"
            )
        # Use '#' as a placeholder because other kinds of arguments are not involved in template instantiation
        return "#"

    def extract(self, args):
        extracted = []
        for arg, kernel_arg in zip(args, self.arguments):
            extracted.append(self.extract_arg(arg, kernel_arg.annotation, kernel_arg.name))
        return tuple(extracted)

    def lookup(self, args):
        if len(args) != self.num_args:
            raise TypeError(f"{self.num_args} argument(s) needed but {len(args)} provided.")

        key = self.extract(args)
        if key not in self.mapping:
            count = len(self.mapping)
            self.mapping[key] = count
        return self.mapping[key], key


def _get_global_vars(_func):
    # Discussions: https://github.com/taichi-dev/taichi/issues/282
    global_vars = _func.__globals__.copy()

    freevar_names = _func.__code__.co_freevars
    closure = _func.__closure__
    if closure:
        freevar_values = list(map(lambda x: x.cell_contents, closure))
        for name, value in zip(freevar_names, freevar_values):
            global_vars[name] = value

    return global_vars


class Kernel:
    counter = 0
    _is_wrapped_kernel = True  # AST call classification; this object cannot execute.

    def __init__(self, _func):
        self.func = _func
        self.kernel_counter = Kernel.counter
        Kernel.counter += 1
        self.arguments = []
        self.return_type = None
        self.extract_arguments()
        self.template_slot_locations = []
        for i, arg in enumerate(self.arguments):
            if isinstance(arg.annotation, template):
                self.template_slot_locations.append(i)
        self.mapper = TaichiCallableTemplateMapper(self.arguments, self.template_slot_locations)
        self.runtime = impl.get_runtime()
        self.kernel_cpp = None
        self.compiled_kernels = {}
        self.has_print = False

    def ast_builder(self):
        assert self.kernel_cpp is not None
        return self.kernel_cpp.ast_builder()

    def extract_arguments(self):
        sig = inspect.signature(self.func)
        if sig.return_annotation not in (inspect._empty, None):
            self.return_type = sig.return_annotation
            if typing.get_origin(self.return_type) is tuple:
                self.return_type = typing.get_args(self.return_type)
            if not isinstance(self.return_type, (list, tuple)):
                self.return_type = (self.return_type,)
            for return_type in self.return_type:
                if return_type is Ellipsis:
                    raise TaichiSyntaxError("Ellipsis is not supported in return type annotations")
        params = sig.parameters
        arg_names = params.keys()
        for i, arg_name in enumerate(arg_names):
            param = params[arg_name]
            if param.kind == inspect.Parameter.VAR_KEYWORD:
                raise TaichiSyntaxError("Taichi kernels do not support variable keyword parameters (i.e., **kwargs)")
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                raise TaichiSyntaxError("Taichi kernels do not support variable positional parameters (i.e., *args)")
            if param.default is not inspect.Parameter.empty:
                raise TaichiSyntaxError("Taichi kernels do not support default values for arguments")
            if param.kind == inspect.Parameter.KEYWORD_ONLY:
                raise TaichiSyntaxError("Taichi kernels do not support keyword parameters")
            if param.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD:
                raise TaichiSyntaxError('Taichi kernels only support "positional or keyword" parameters')
            annotation = param.annotation
            if param.annotation is inspect.Parameter.empty:
                raise TaichiSyntaxError("Compiler kernel parameters must be type annotated")
            else:
                if isinstance(
                    annotation,
                    (template, buffer_type.BufferType),
                ):
                    pass
                elif id(annotation) in primitive_types.type_ids:
                    pass
                elif isinstance(annotation, MatrixType):
                    pass
                elif isinstance(annotation, StructType):
                    pass
                else:
                    raise TaichiSyntaxError(f"Invalid type annotation (argument {i}) of Taichi kernel: {annotation}")
            self.arguments.append(KernelArgument(annotation, param.name, param.default))

    def materialize(self, key=None, args=None, arg_features=None):
        if key is None:
            key = (self.func, 0)

        if key in self.compiled_kernels:
            return

        kernel_name = f"{self.func.__name__}_c{self.kernel_counter}_{key[1]}"
        _logging.trace(f"Compiling kernel {kernel_name}...")

        tree, ctx = _get_tree_and_ctx(
            self,
            args=args,
            excluded_parameters=self.template_slot_locations,
            arg_features=arg_features,
        )

        # Do not change the name of 'taichi_ast_generator'
        # The warning system needs this identifier to remove unnecessary messages
        def taichi_ast_generator(kernel_cxx):
            if self.runtime.inside_kernel:
                raise TaichiSyntaxError(
                    "Kernels cannot call other kernels. I.e., nested kernels are not allowed. "
                    "Please check if you have direct/indirect invocation of kernels within kernels. "
                    "Note that some methods provided by the Taichi standard library may invoke kernels, "
                    "and please move their invocations to Python-scope."
                )
            self.kernel_cpp = kernel_cxx
            self.runtime.inside_kernel = True
            self.runtime.current_kernel = self
            assert self.runtime.compiling_callable is None
            self.runtime.compiling_callable = kernel_cxx
            try:
                ctx.ast_builder = kernel_cxx.ast_builder()
                transform_tree(tree, ctx)
                if self.return_type and ctx.returned != ReturnStatus.ReturnedValue:
                    raise TaichiSyntaxError("Kernel has a return type but does not have a return statement")
            finally:
                self.runtime.inside_kernel = False
                self.runtime.current_kernel = None
                self.runtime.compiling_callable = None
                self.kernel_cpp = None

        taichi_kernel = impl.get_runtime().prog.create_kernel(kernel_name)
        taichi_ast_generator(taichi_kernel)
        assert key not in self.compiled_kernels
        self.compiled_kernels[key] = taichi_kernel

    def ensure_compiled(self, *args):
        instance_id, arg_features = self.mapper.lookup(args)
        key = (self.func, instance_id)
        self.materialize(key=key, args=args, arg_features=arg_features)
        return key

    def __call__(self, *args, **kwargs):
        raise TaichiRuntimeError(
            "The private Infernux compiler frontend cannot execute kernels; "
            "use inx.compute.launch()"
        )


def kernel(fn):
    """Create one compiler kernel; execution belongs to Infernux."""
    return Kernel(fn)


__all__ = ["func", "kernel", "pyfunc"]
