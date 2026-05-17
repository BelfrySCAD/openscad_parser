"""Extract assignments: find all variable assignments and their value types."""

import dataclasses
from openscad_parser.ast import getASTfromString, ASTNode
from openscad_parser.ast.nodes import (
    Assignment, ModuleDeclaration, FunctionDeclaration,
    NumberLiteral, StringLiteral, BooleanLiteral, UndefinedLiteral,
    ListComprehension,
)

CODE = """\
// Global configuration
width = 100;
height = 50;
depth = 30;
label = "Part A";
centered = true;
scale_factor = undef;

// Derived values
volume = width * height * depth;
diagonal = sqrt(width^2 + height^2);
points = [for (i = [0:5]) i * width / 5];

module part(w = width, h = height) {
    inner_margin = 2;
    cube([w - inner_margin, h - inner_margin, depth]);
}

function area(w, h) = w * h;
"""


def expr_summary(expr) -> str:
    """Return a short human-readable description of an expression."""
    if isinstance(expr, NumberLiteral):
        return f"number ({expr.val})"
    if isinstance(expr, StringLiteral):
        return f'string ("{expr.val}")'
    if isinstance(expr, BooleanLiteral):
        return f"bool ({expr.val})"
    if isinstance(expr, UndefinedLiteral):
        return "undef"
    if isinstance(expr, ListComprehension):
        return "list comprehension"
    return type(expr).__name__


def find_assignments(nodes, scope_name="<top level>", depth=0):
    """Recursively find all Assignment nodes, noting their scope."""
    for node in nodes:
        if not isinstance(node, ASTNode):
            continue
        if isinstance(node, Assignment):
            indent = "  " * depth
            print(f"{indent}{scope_name}:  {node.name.name} = {expr_summary(node.expr)}")
        elif isinstance(node, ModuleDeclaration):
            find_assignments(node.children, scope_name=f"module {node.name.name}", depth=depth + 1)
        elif isinstance(node, FunctionDeclaration):
            pass  # function bodies are single expressions, no nested assignments


def main():
    ast = getASTfromString(CODE)
    print("Variable assignments found:\n")
    find_assignments(ast)


if __name__ == "__main__":
    main()
