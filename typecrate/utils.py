import functools
import inspect
from typing import Iterable

from typecrate.exceptions import BuiltinFunctionsError


def is_iterable(obj):
    return isinstance(obj, Iterable)


# From: django-rest-framework/fields
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

    sig = inspect.signature(obj)
    params = sig.parameters.values()
    return all(
        param.kind == param.VAR_POSITIONAL or
        param.kind == param.VAR_KEYWORD or
        param.default != param.empty
        for param in params
    )
