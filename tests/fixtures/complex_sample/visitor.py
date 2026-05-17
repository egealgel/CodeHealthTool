import ast


class Counter(ast.NodeVisitor):
    def __init__(self):
        self.calls = 0
        self.funcs = 0

    def visit_Call(self, node):
        self.calls += 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.funcs += 1
        self.generic_visit(node)


def count_in_source(source: str) -> tuple[int, int]:
    tree = ast.parse(source)
    c = Counter()
    c.visit(tree)
    return c.calls, c.funcs
