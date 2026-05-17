from .live import used_function, UsedClass

__all__ = ["used_function", "UsedClass", "exported_dead_name"]


def exported_dead_name():
    # Listed in __all__, should NOT be reported as dead.
    return 1
