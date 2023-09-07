class BuiltinFunctionsError(Exception):
    """
    Built-in function are not usable
    """

    pass


class ValueDoesNotExist(Exception):
    """
    If given source is not found in the source, raise this exception
    """


class InvalidSourceExpression(Exception):
    """
    Only when the grammar of the source expression is not valid
    """