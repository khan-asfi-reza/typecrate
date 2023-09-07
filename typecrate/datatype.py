class _null:
    """
    Null class type, to represent Null value or empty value
    """

    @staticmethod
    def to_value():
        return None

    def __bool__(self):
        return False

    def __repr__(self):
        return "Null"

    def __str__(self):
        return "Null"

    def __eq__(self, other):
        return type(self) is type(other)


class Empty:
    pass


Null = _null()


class NonExistent:
    @staticmethod
    def to_value():
        return None

    def __bool__(self):
        return False

    def __repr__(self):
        return "NonExistent"

    def __str__(self):
        return "NonExistent"

    def __eq__(self, other):
        return type(self) is type(other)
