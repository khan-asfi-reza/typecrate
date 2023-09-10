import functools
import inspect
from typing import Iterable, Mapping

from typecrate.exceptions import BuiltinFunctionsError, ValueDoesNotExist


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


def get_attribute(instance, attr):
    """
    Like python's getattr function, but it works on both mapping and objects
    """
    try:
        if isinstance(instance, Mapping):
            instance = instance[attr]
        else:
            instance = getattr(instance, attr)
    except (KeyError, AttributeError):
        raise ValueDoesNotExist(
            "Value doesn't exist for key `{}`".format(
                attr
            )
        )
    if is_callable(instance):
        try:
            instance = instance()
        except (AttributeError, KeyError) as exc:
            raise ValueError(
                "Exception raised while calling the attribute `{}`; "
                "original exception was: {}".format(
                    attr, exc)
            )

    return instance
