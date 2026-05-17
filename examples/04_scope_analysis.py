"""Scope analysis: use build_scopes() to inspect variable, function, and module bindings."""

from openscad_parser.ast import getASTfromString, build_scopes
from openscad_parser.ast.nodes import (
    Assignment, ModuleDeclaration, FunctionDeclaration, ModularCall,
)

CODE = """\
// Top-level variables
width = 100;
height = 50;

function area(w, h) = w * h;
function perimeter(w, h) = 2 * (w + h);

module box(w = width, h = height, d = 10) {
    wall = 2;
    cube([w, h, d]);
    translate([wall, wall, d])
        cube([w - 2*wall, h - 2*wall, 1]);
}

module lid(w = width, h = height) {
    thickness = 1.5;
    cube([w, h, thickness]);
}

box();
lid(w = 120);
"""


def print_scope(scope, name="<root>", indent=0):
    pad = "  " * indent
    print(f"{pad}Scope: {name}")
    if scope.variables:
        print(f"{pad}  variables : {', '.join(scope.variables)}")
    if scope.functions:
        print(f"{pad}  functions : {', '.join(scope.functions)}")
    if scope.modules:
        print(f"{pad}  modules   : {', '.join(scope.modules)}")


def main():
    ast = getASTfromString(CODE)
    root_scope = build_scopes(ast)

    print("=== Scope tree ===\n")
    print_scope(root_scope)

    print("\n=== Per-declaration inner scopes ===\n")
    for node in ast:
        if isinstance(node, FunctionDeclaration):
            inner = node.expr.scope
            print_scope(inner, name=f"function {node.name.name}", indent=1)
        elif isinstance(node, ModuleDeclaration):
            if node.children:
                inner = node.children[0].scope
                print_scope(inner, name=f"module {node.name.name}", indent=1)

    print("\n=== Variable lookup from a module call ===\n")
    calls = [n for n in ast if isinstance(n, ModularCall)]
    for call in calls:
        scope = call.scope
        w = scope.lookup_variable("width")
        h = scope.lookup_variable("height")
        fn = scope.lookup_function("area")
        mod = scope.lookup_module("box")
        print(f"  At call '{call.name}' (line {call.position.line}):")
        print(f"    lookup width    -> {type(w).__name__ if w else None}")
        print(f"    lookup height   -> {type(h).__name__ if h else None}")
        print(f"    lookup area()   -> {type(fn).__name__ if fn else None}")
        print(f"    lookup module box -> {type(mod).__name__ if mod else None}")


if __name__ == "__main__":
    main()
