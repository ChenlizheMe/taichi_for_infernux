# Modified by Infernux in 2026: host interchange uses NumPy, not tensor frameworks.
import numbers
from types import MethodType

import numpy as np
from .._lib import core as _ti_core
from . import expr, impl, ops
from .exception import (
    TaichiRuntimeTypeError,
    TaichiSyntaxError,
    TaichiTypeError,
)
from .expr import Expr
from .matrix import Matrix, MatrixType
from .util import cook_dtype, in_python_scope, python_scope, taichi_scope
from ..types import primitive_types
from ..types.compound_types import CompoundType
from ..types.utils import is_signed


class Struct:
    """The Struct type class.

    A struct is a dictionary-like data structure that stores members as
    (key, value) pairs. Valid data members of a struct can be scalars,
    matrices or other dictionary-like structures.

    Args:
        entries (Dict[str, Union[Dict, Expr, Matrix, Struct]]): \
            keys and values for struct members. Entries can optionally
            include a dictionary of functions with the key '__struct_methods'
            which will be attached to the struct for executing on the struct data.

    Returns:
        An instance of this struct.

    Example::
_
        >>> vec3 = ti.types.vector(3, ti.f32)
        >>> a = ti.Struct(v=vec3([0, 0, 0]), t=1.0)
        >>> print(a.items)
        dict_items([('v', [0. 0. 0.]), ('t', 1.0)])
        >>>
        >>> B = ti.Struct(v=vec3([0., 0., 0.]), t=1.0, A=a)
        >>> print(B.items)
        dict_items([('v', [0. 0. 0.]), ('t', 1.0), ('A', {'v': [[0.], [0.], [0.]], 't': 1.0})])
    """

    _is_taichi_class = True
    _instance_count = 0

    def __init__(self, *args, **kwargs):
        # converts lists to matrices and dicts to structs
        if len(args) == 1 and kwargs == {} and isinstance(args[0], dict):
            self.__entries = args[0]
        elif len(args) == 0:
            self.__entries = kwargs
        else:
            raise TaichiSyntaxError(
                "Custom structs need to be initialized using either dictionary or keyword arguments"
            )
        self.__methods = self.__entries.pop("__struct_methods", {})
        matrix_ndim = self.__entries.pop("__matrix_ndim", {})
        self._register_methods()

        for k, v in self.__entries.items():
            if isinstance(v, (list, tuple)):
                v = Matrix(v)
            if isinstance(v, dict):
                v = Struct(v)
            self.__entries[k] = v if in_python_scope() else impl.expr_init(v)
        self._register_members()
        self.__dtype = None

    @property
    def keys(self):
        """Returns the list of member names in string format.

        Example::

           >>> vec3 = ti.types.vector(3, ti.f32)
           >>> sphere = ti.Struct(center=vec3([0, 0, 0]), radius=1.0)
           >>> a.keys
           ['center', 'radius']
        """
        return list(self.__entries.keys())

    @property
    def _members(self):
        return list(self.__entries.values())

    @property
    def entries(self):
        return self.__entries

    @property
    def methods(self):
        return self.__methods

    @property
    def items(self):
        """Returns the items in this struct.

        Example::

            >>> vec3 = ti.types.vector(3, ti.f32)
            >>> sphere = ti.Struct(center=vec3([0, 0, 0]), radius=1.0)
            >>> sphere.items
            dict_items([('center', 2), ('radius', 1.0)])
        """
        return self.__entries.items()

    def _register_members(self):
        # https://stackoverflow.com/questions/48448074/adding-a-property-to-an-existing-object-instance
        cls = self.__class__
        new_cls_name = cls.__name__ + str(cls._instance_count)
        cls._instance_count += 1
        properties = {k: property(cls._make_getter(k), cls._make_setter(k)) for k in self.keys}
        self.__class__ = type(new_cls_name, (cls,), properties)

    def _register_methods(self):
        for name, method in self.__methods.items():
            # use MethodType to pass self (this object) to the method
            setattr(self, name, MethodType(method, self))

    def __getitem__(self, key):
        return self.__entries[key]

    def __setitem__(self, key, value):
        if in_python_scope():
            if isinstance(self.__entries[key], Struct) or isinstance(self.__entries[key], Matrix):
                self.__entries[key]._set_entries(value)
            elif isinstance(value, numbers.Number):
                self.__entries[key] = value
            else:
                raise TypeError("A number is expected when assigning struct members")
        else:
            self.__entries[key] = value

    def _set_entries(self, value):
        if isinstance(value, dict):
            value = Struct(value)
        for k in self.keys:
            self[k] = value[k]
        self.__dtype = value.__dtype

    @staticmethod
    def _make_getter(key):
        def getter(self):
            """Get an entry from custom struct by name."""
            return self[key]

        return getter

    @staticmethod
    def _make_setter(key):
        @python_scope
        def setter(self, value):
            self[key] = value

        return setter

    @taichi_scope
    def _assign(self, other):
        if not isinstance(other, (dict, Struct)):
            raise TaichiTypeError("Only dict or Struct can be assigned to a Struct")
        if isinstance(other, dict):
            other = Struct(other)
        if self.__entries.keys() != other.__entries.keys():
            raise TaichiTypeError(f"Member mismatch between structs {self.keys}, {other.keys}")
        for k, v in self.items:
            v._assign(other.__entries[k])
        self.__dtype = other.__dtype
        return self

    def __len__(self):
        """Get the number of entries in a custom struct"""
        return len(self.__entries)

    def __iter__(self):
        return self.__entries.values()

    def __str__(self):
        """Python scope struct array print support."""
        if impl.inside_kernel():
            item_str = ", ".join([str(k) + "=" + str(v) for k, v in self.items])
            item_str += f", struct_methods={self.__methods}"
            return f"<ti.Struct {item_str}>"
        return str(self.to_dict())

    def __repr__(self):
        return str(self.to_dict())

    def to_dict(self, include_methods=False, include_ndim=False):
        """Converts the Struct to a dictionary.

        Args:
            include_methods (bool): Whether any struct methods should be included
                in the result dictionary under the key '__struct_methods'.

        Returns:
            Dict: The result dictionary.
        """
        res_dict = {
            k: (
                v.to_dict(include_methods=include_methods, include_ndim=include_ndim)
                if isinstance(v, Struct)
                else v.to_list() if isinstance(v, Matrix) else v
            )
            for k, v in self.__entries.items()
        }
        if include_methods:
            res_dict["__struct_methods"] = self.__methods
        if include_ndim:
            res_dict["__matrix_ndim"] = dict()
            for k, v in self.__entries.items():
                if isinstance(v, Matrix):
                    res_dict["__matrix_ndim"][k] = v.ndim
        return res_dict

class _IntermediateStruct(Struct):
    """Intermediate struct class for compiler internal use only.

    Args:
        entries (Dict[str, Union[Expr, Matrix, Struct]]): keys and values for struct members.
            Any methods included under the key '__struct_methods' will be applied to each
            struct instance.
    """

    def __init__(self, entries):
        assert isinstance(entries, dict)
        self._Struct__methods = entries.pop("__struct_methods", {})
        self._register_methods()
        self._Struct__entries = entries
        self._register_members()


class StructType(CompoundType):
    def __init__(self, **kwargs):
        self.members = {}
        self.methods = {}
        elements = []
        for k, dtype in kwargs.items():
            if k == "__struct_methods":
                self.methods = dtype
            elif isinstance(dtype, StructType):
                self.members[k] = dtype
                elements.append([dtype.dtype, k])
            elif isinstance(dtype, MatrixType):
                self.members[k] = dtype
                elements.append([dtype.tensor_type, k])
            else:
                dtype = cook_dtype(dtype)
                self.members[k] = dtype
                elements.append([dtype, k])
        self.dtype = _ti_core.get_type_factory_instance().get_struct_type(elements)

    def __call__(self, *args, **kwargs):
        """Create an instance of this struct type."""
        d = {}
        items = self.members.items()
        # iterate over the members of this struct
        for index, pair in enumerate(items):
            name, dtype = pair  # (member name, member type)
            if index < len(args):  # set from args
                data = args[index]
            else:  # set from kwargs
                data = kwargs.get(name, 0)

            # If dtype is CompoundType and data is a scalar, it cannot be
            # casted in the self.cast call later. We need an initialization here.
            if isinstance(dtype, CompoundType) and not isinstance(data, (dict, Struct)):
                data = dtype(data)

            d[name] = data

        entries = Struct(d)
        entries._Struct__dtype = self.dtype
        struct = self.cast(entries)
        struct._Struct__dtype = self.dtype
        return struct

    def __instancecheck__(self, instance):
        if not isinstance(instance, Struct):
            return False
        if list(self.members.keys()) != list(instance._Struct__entries.keys()):
            return False
        if (
            hasattr(instance, "_Struct__dtype")
            and instance._Struct__dtype is not None
            and instance._Struct__dtype != self.dtype
        ):
            return False
        for index, (name, dtype) in enumerate(self.members.items()):
            val = instance._members[index]
            if isinstance(dtype, StructType):
                if not isinstance(val, dtype):
                    return False
            elif isinstance(dtype, MatrixType):
                if isinstance(val, Expr):
                    if not val.is_tensor():
                        return False
                if val.get_shape() != dtype.get_shape():
                    return False
            elif dtype in primitive_types.integer_types:
                if isinstance(val, Expr):
                    if val.is_tensor() or val.is_struct() or val.element_type() not in primitive_types.integer_types:
                        return False
                elif not isinstance(val, (int, np.integer)):
                    return False
            elif dtype in primitive_types.real_types:
                if isinstance(val, Expr):
                    if val.is_tensor() or val.is_struct() or val.element_type() not in primitive_types.real_types:
                        return False
                elif not isinstance(val, (float, np.floating)):
                    return False
        return True

    def from_taichi_object(self, func_ret, ret_index=()):
        d = {}
        items = self.members.items()
        for index, pair in enumerate(items):
            name, dtype = pair
            if isinstance(dtype, CompoundType):
                d[name] = dtype.from_taichi_object(func_ret, ret_index + (index,))
            else:
                d[name] = expr.Expr(
                    _ti_core.make_get_element_expr(
                        func_ret.ptr,
                        ret_index + (index,),
                        _ti_core.DebugInfo(impl.get_runtime().get_current_src_info()),
                    )
                )
        d["__struct_methods"] = self.methods

        struct = Struct(d)
        struct._Struct__dtype = self.dtype
        return struct

    def from_kernel_struct_ret(self, launch_ctx, ret_index=()):
        d = {}
        items = self.members.items()
        for index, pair in enumerate(items):
            name, dtype = pair
            if isinstance(dtype, CompoundType):
                d[name] = dtype.from_kernel_struct_ret(launch_ctx, ret_index + (index,))
            else:
                if dtype in primitive_types.integer_types:
                    if is_signed(cook_dtype(dtype)):
                        d[name] = launch_ctx.get_struct_ret_int(ret_index + (index,))
                    else:
                        d[name] = launch_ctx.get_struct_ret_uint(ret_index + (index,))
                elif dtype in primitive_types.real_types:
                    d[name] = launch_ctx.get_struct_ret_float(ret_index + (index,))
                else:
                    raise TaichiRuntimeTypeError(f"Invalid return type on index={ret_index + (index, )}")
        d["__struct_methods"] = self.methods

        struct = Struct(d)
        struct._Struct__dtype = self.dtype
        return struct

    def set_kernel_struct_args(self, struct, launch_ctx, ret_index=()):
        # TODO: move this to class Struct after we add dtype to Struct
        items = self.members.items()
        for index, pair in enumerate(items):
            name, dtype = pair
            if isinstance(dtype, CompoundType):
                dtype.set_kernel_struct_args(struct[name], launch_ctx, ret_index + (index,))
            else:
                if dtype in primitive_types.integer_types:
                    if is_signed(cook_dtype(dtype)):
                        launch_ctx.set_struct_arg_int(ret_index + (index,), struct[name])
                    else:
                        launch_ctx.set_struct_arg_uint(ret_index + (index,), struct[name])
                elif dtype in primitive_types.real_types:
                    launch_ctx.set_struct_arg_float(ret_index + (index,), struct[name])
                else:
                    raise TaichiRuntimeTypeError(f"Invalid argument type on index={ret_index + (index, )}")

    def set_argpack_struct_args(self, struct, argpack, ret_index=()):
        # TODO: move this to class Struct after we add dtype to Struct
        items = self.members.items()
        for index, pair in enumerate(items):
            name, dtype = pair
            if isinstance(dtype, CompoundType):
                dtype.set_kernel_struct_args(struct[name], argpack, ret_index + (index,))
            else:
                if dtype in primitive_types.integer_types:
                    if is_signed(cook_dtype(dtype)):
                        argpack.set_arg_int(ret_index + (index,), struct[name])
                    else:
                        argpack.set_arg_uint(ret_index + (index,), struct[name])
                elif dtype in primitive_types.real_types:
                    argpack.set_arg_float(ret_index + (index,), struct[name])
                else:
                    raise TaichiRuntimeTypeError(f"Invalid argument type on index={ret_index + (index, )}")

    def cast(self, struct):
        # sanity check members
        if self.members.keys() != struct._Struct__entries.keys():
            raise TaichiSyntaxError("Incompatible arguments for custom struct members!")
        entries = {}
        for k, dtype in self.members.items():
            if isinstance(dtype, MatrixType):
                entries[k] = dtype(struct._Struct__entries[k])
            elif isinstance(dtype, CompoundType):
                entries[k] = dtype.cast(struct._Struct__entries[k])
            else:
                if in_python_scope():
                    v = struct._Struct__entries[k]
                    entries[k] = int(v) if dtype in primitive_types.integer_types else float(v)
                else:
                    entries[k] = ops.cast(struct._Struct__entries[k], dtype)
        entries["__struct_methods"] = self.methods
        struct = Struct(entries)
        struct._Struct__dtype = self.dtype
        return struct

    def filled_with_scalar(self, value):
        entries = {}
        for k, dtype in self.members.items():
            if isinstance(dtype, MatrixType):
                entries[k] = dtype(value)
            elif isinstance(dtype, CompoundType):
                entries[k] = dtype.filled_with_scalar(value)
            else:
                entries[k] = value
        entries["__struct_methods"] = self.methods
        struct = Struct(entries)
        struct._Struct__dtype = self.dtype
        return struct

    def __str__(self):
        """Python scope struct type print support."""
        item_str = ", ".join([str(k) + "=" + str(v) for k, v in self.members.items()])
        item_str += f", struct_methods={self.methods}"
        return f"<ti.StructType {item_str}>"


def dataclass(cls):
    """Converts a class with field annotations and methods into a taichi struct type.

    This will return a normal custom struct type, with the functions added to it.
    Struct fields can be generated in the normal way from the struct type.
    Functions in the class can be run on the struct instance.

    This class decorator inspects the class for annotations and methods and
        1.  Sets the annotations as fields for the struct
        2.  Attaches the methods to the struct type

    Example::

        >>> @ti.dataclass
        >>> class Sphere:
        >>>     center: vec3
        >>>     radius: ti.f32
        >>>
        >>>     @ti.func
        >>>     def area(self):
        >>>         return 4 * 3.14 * self.radius * self.radius
        >>>
        >>> my_spheres = Sphere.field(shape=(n, ))
        >>> my_sphere[2].area()

    Args:
        cls (Class): the class with annotations and methods to convert to a struct

    Returns:
        A taichi struct with the annotations as fields
            and methods from the class attached.
    """
    # save the annotation fields for the struct
    fields = getattr(cls, "__annotations__", {})
    # raise error if there are default values
    for k in fields.keys():
        if hasattr(cls, k):
            raise TaichiSyntaxError("Default value in @dataclass is not supported.")
    # get the class methods to be attached to the struct types
    fields["__struct_methods"] = {
        attribute: getattr(cls, attribute)
        for attribute in dir(cls)
        if callable(getattr(cls, attribute)) and not attribute.startswith("__")
    }
    return StructType(**fields)


__all__ = ["Struct", "dataclass"]
