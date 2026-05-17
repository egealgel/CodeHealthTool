_HANDLERS = {}


def register(name):
    def decorator(fn):
        _HANDLERS[name] = fn
        return fn
    return decorator


@register("hello")
def say_hello(target):
    return f"hello {target}"


@register("bye")
def say_bye(target):
    return f"bye {target}"


def dispatch(name, target):
    return _HANDLERS[name](target)
