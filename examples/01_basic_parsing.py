"""Basic parsing: parse an OpenSCAD string and inspect the resulting AST."""

import dataclasses
from openscad_parser.ast import getASTfromString, ASTNode

CODE = """\
// A simple OpenSCAD model
width = 20;
height = 10;

module box(w, h) {
    cube([w, h, h]);
}

box(width, height);
translate([30, 0, 0]) sphere(r = 5);
"""


def walk(node):
    """Yield every ASTNode in the tree, depth-first."""
    if not isinstance(node, ASTNode):
        return
    yield node
    for f in dataclasses.fields(node):
        if f.name in ("position", "scope"):
            continue
        val = getattr(node, f.name)
        if isinstance(val, list):
            for item in val:
                yield from walk(item)
        else:
            yield from walk(val)


def main():
    ast = getASTfromString(CODE, include_comments=True)

    print(f"Top-level nodes: {len(ast)}\n")
    for node in ast:
        print(f"  {type(node).__name__:30s}  line {node.position.line}")

    print(f"\nAll nodes in tree:")
    for node in ast:
        for n in walk(node):
            indent = "  "
            print(f"{indent}{type(n).__name__:30s}  line {n.position.line}, col {n.position.column}")


if __name__ == "__main__":
    main()
