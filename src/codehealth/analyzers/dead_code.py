from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


DUNDER_WHITELIST = {
    "__init__", "__new__", "__del__", "__repr__", "__str__", "__bytes__",
    "__format__", "__hash__", "__bool__", "__call__",
    "__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__",
    "__enter__", "__exit__", "__aenter__", "__aexit__",
    "__iter__", "__next__", "__aiter__", "__anext__",
    "__len__", "__contains__", "__getitem__", "__setitem__", "__delitem__",
    "__getattr__", "__setattr__", "__delattr__", "__getattribute__",
    "__add__", "__sub__", "__mul__", "__truediv__", "__floordiv__",
    "__mod__", "__pow__", "__and__", "__or__", "__xor__",
    "__radd__", "__rsub__", "__rmul__",
    "__post_init__", "__init_subclass__", "__class_getitem__", "__set_name__",
    "__index__", "__length_hint__", "__reversed__",
    "__copy__", "__deepcopy__", "__reduce__", "__reduce_ex__",
    "__getstate__", "__setstate__",
}

TEST_FUNC_PREFIXES = ("test_",)
TEST_CLASS_PREFIXES = ("Test",)

# Decorators that do NOT change how the decorated symbol is referenced
# (they wrap behavior but the name is still the only call site).
SAFE_DECORATORS = {
    "dataclass", "dataclasses.dataclass",
    "property", "staticmethod", "classmethod",
    "abstractmethod", "abc.abstractmethod",
    "abstractproperty", "abc.abstractproperty",
    "cached_property", "functools.cached_property",
    "lru_cache", "functools.lru_cache",
    "cache", "functools.cache",
    "wraps", "functools.wraps",
    "total_ordering", "functools.total_ordering",
    "singledispatch", "functools.singledispatch",
    "singledispatchmethod", "functools.singledispatchmethod",
    "final", "typing.final",
    "override", "typing.override",
    "runtime_checkable", "typing.runtime_checkable",
    "no_type_check", "typing.no_type_check",
}

# Method-name prefixes that are usually invoked via dynamic dispatch
# (only honored when the enclosing class looks like a dispatcher).
DISPATCH_PREFIXES = ("visit_", "do_", "handle_", "p_")
DISPATCH_BASE_HINTS = ("Visitor", "Handler", "Dispatcher", "Transformer")


@dataclass(frozen=True)
class Definition:
    name: str
    file: str
    line: int
    kind: str  # "function" | "class" | "method"
    decorated_unsafe: bool
    dynamic_dispatch: bool = False


@dataclass
class DeadCodeReport:
    dead: list[Definition] = field(default_factory=list)
    maybe: list[Definition] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.dead) + len(self.maybe)


def analyze(root: Path) -> DeadCodeReport:
    root = Path(root)
    files = _python_files(root)

    definitions: list[Definition] = []
    references: set[str] = set()
    all_exports: set[str] = set()

    for f in files:
        try:
            source = f.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(f))
        except (UnicodeDecodeError, SyntaxError):
            continue

        all_exports.update(_collect_all_exports(tree))
        definitions.extend(_collect_definitions(tree, f))
        references.update(_collect_references(tree))

    report = DeadCodeReport()
    for d in definitions:
        if _is_excluded(d, all_exports):
            continue
        if d.name in references:
            continue
        if d.dynamic_dispatch:
            continue
        if d.decorated_unsafe:
            report.maybe.append(d)
        else:
            report.dead.append(d)
    return report


def _python_files(root: Path) -> list[Path]:
    if root.is_file() and root.suffix == ".py":
        return [root]
    return [
        p for p in root.rglob("*.py")
        if not _is_in_excluded_dir(p)
    ]


def _is_in_excluded_dir(p: Path) -> bool:
    parts = set(p.parts)
    excluded = {".git", ".venv", "venv", "env", "__pycache__", "build", "dist", ".tox"}
    return bool(parts & excluded)


def _collect_all_exports(tree: ast.AST) -> set[str]:
    exports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        for elt in node.value.elts:
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                exports.add(elt.value)
    return exports


def _decorator_name(dec: ast.AST) -> str:
    if isinstance(dec, ast.Call):
        return _decorator_name(dec.func)
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        # build full dotted name
        parts = []
        cur: ast.AST = dec
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
            return ".".join(reversed(parts))
        return dec.attr
    return ""


def _is_decorated_unsafe(node: ast.AST) -> bool:
    decorators = getattr(node, "decorator_list", []) or []
    if not decorators:
        return False
    return any(_decorator_name(d) not in SAFE_DECORATORS for d in decorators)


def _class_is_dispatcher(cls: ast.ClassDef) -> bool:
    for base in cls.bases:
        name = _decorator_name(base)  # works for Name / Attribute
        if not name:
            continue
        tail = name.rsplit(".", 1)[-1]
        if any(h in tail for h in DISPATCH_BASE_HINTS):
            return True
    return False


def _collect_definitions(tree: ast.AST, file: Path) -> list[Definition]:
    defs: list[Definition] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self):
            self.class_stack: list[ast.ClassDef] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            defs.append(Definition(
                name=node.name,
                file=str(file),
                line=node.lineno,
                kind="class",
                decorated_unsafe=_is_decorated_unsafe(node),
            ))
            self.class_stack.append(node)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_func(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_func(node)

        def _visit_func(self, node) -> None:
            kind = "method" if self.class_stack else "function"
            dynamic = False
            if self.class_stack and _class_is_dispatcher(self.class_stack[-1]):
                if any(node.name.startswith(p) for p in DISPATCH_PREFIXES):
                    dynamic = True
            defs.append(Definition(
                name=node.name,
                file=str(file),
                line=node.lineno,
                kind=kind,
                decorated_unsafe=_is_decorated_unsafe(node),
                dynamic_dispatch=dynamic,
            ))
            self.generic_visit(node)

    Visitor().visit(tree)
    return defs


def _collect_references(tree: ast.AST) -> set[str]:
    refs: set[str] = set()

    def add_from_annotation(ann: ast.AST | None) -> None:
        if ann is None:
            return
        if isinstance(ann, ast.Constant) and isinstance(ann.value, str):
            try:
                sub = ast.parse(ann.value, mode="eval")
            except SyntaxError:
                return
            for n in ast.walk(sub):
                if isinstance(n, ast.Name):
                    refs.add(n.id)
                elif isinstance(n, ast.Attribute):
                    refs.add(n.attr)

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                refs.add(alias.name)
                if alias.asname:
                    refs.add(alias.asname)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                base = alias.name.split(".")[0]
                refs.add(base)
                if alias.asname:
                    refs.add(alias.asname)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (
                node.args.args
                + node.args.kwonlyargs
                + node.args.posonlyargs
            ):
                add_from_annotation(arg.annotation)
            if node.args.vararg:
                add_from_annotation(node.args.vararg.annotation)
            if node.args.kwarg:
                add_from_annotation(node.args.kwarg.annotation)
            add_from_annotation(node.returns)
        elif isinstance(node, ast.AnnAssign):
            add_from_annotation(node.annotation)
    return refs


def _is_excluded(d: Definition, all_exports: set[str]) -> bool:
    if d.name in DUNDER_WHITELIST:
        return True
    if d.name.startswith("__") and d.name.endswith("__"):
        return True
    if d.kind in ("function", "method") and any(d.name.startswith(p) for p in TEST_FUNC_PREFIXES):
        return True
    if d.kind == "class" and any(d.name.startswith(p) for p in TEST_CLASS_PREFIXES):
        return True
    if d.name in all_exports:
        return True
    if d.name == "main":
        return True
    return False
