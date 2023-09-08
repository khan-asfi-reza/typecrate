from typing import Any


class EArray:
    """
    Special array to store value
    """

    def __init__(self, unique=False, array=None):
        if not array:
            array = []
        self._array = array
        self.unique = unique

    @property
    def array(self):
        return list(self._array) if not self.unique else list(set(self._array))

    def __getitem__(self, index):
        return self.array[index]

    def __setitem__(self, index, value):
        self._array[index] = value

    def __delitem__(self, index):
        del self._array[index]

    def __len__(self):
        return len(self.array)

    def __add__(self, other):
        if type(other) is list:
            new_array = self._array + other
            return EArray(unique=self.unique, array=new_array)
        elif type(other) is EArray:
            return EArray(unique=self.unique or other.unique, array=self.array + other.array)

    def __iadd__(self, other):
        if type(other) is list:
            new_array = self._array + other
            return EArray(unique=self.unique, array=new_array)
        elif type(other) is EArray:
            return EArray(unique=self.unique or other.unique, array=self.array + other.array)

    def insert(self, elem: Any):
        self._array.append(elem)
