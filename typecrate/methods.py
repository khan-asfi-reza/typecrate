class ClassProperty(object):
    def __init__(self, f_get, f_set=None):
        self.f_get = f_get
        self.f_set = f_set

    def __get__(self, obj, klass=None):
        if klass is None:
            klass = type(obj)
        return self.f_get.__get__(obj, klass)()

    def __set__(self, obj, value):
        if not self.f_set:
            raise AttributeError("can't set attribute")
        type_ = type(obj)
        return self.f_set.__get__(obj, type_)(value)

    def setter(self, func):
        if not isinstance(func, (classmethod, staticmethod)):
            func = classmethod(func)
        self.f_set = func
        return self


def classproperty(func):
    if not isinstance(func, (classmethod, staticmethod)):
        func = classmethod(func)

    return ClassProperty(func)
