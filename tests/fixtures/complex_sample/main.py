from .models import Dog
from .registry import dispatch
from .typed import use_consume
from .visitor import count_in_source


def run():
    d = Dog("rex")
    print(d.speak())
    print(dispatch("hello", "world"))
    print(count_in_source("x = 1\n"))
    print(use_consume())


def truly_dead():
    return "nobody calls me"
