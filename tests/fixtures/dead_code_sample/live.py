class UsedClass:
    def __init__(self, x):
        self.x = x

    def method_called(self):
        return self.x


def used_function():
    obj = UsedClass(5)
    return obj.method_called()


def unused_helper():
    return "nobody calls me"


class LegacyAdapter:
    def __init__(self):
        pass

    def adapt(self):
        return None
