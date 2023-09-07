import functools
import inspect
from typing import Iterable

from typecrate.exceptions import BuiltinFunctionsError


def is_iterable(obj):
    return isinstance(obj, Iterable)


def is_callable(obj):
    """
    True if the object is a callable.
    """
    if not callable(obj):
        return False

    # Bail early since we cannot inspect built-in function signatures.
    if inspect.isbuiltin(obj):
        raise BuiltinFunctionsError("Built-in functions are not usable. ")

    if not (
        inspect.isfunction(obj)
        or inspect.ismethod(obj)
        or isinstance(obj, functools.partial)
    ):
        return False

    return True
