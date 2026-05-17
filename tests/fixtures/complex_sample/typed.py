from __future__ import annotations


class OnlyUsedAsType:
    pass


class StringAnnotated:
    pass


def consume(x: OnlyUsedAsType) -> "StringAnnotated":
    return None  # type: ignore[return-value]


def use_consume():
    return consume(OnlyUsedAsType())
