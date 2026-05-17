"""Find all module calls: collect every ModularCall node in the AST."""

import dataclasses
from openscad_parser.ast import getASTfromString, ASTNode
from openscad_parser.ast.nodes import ModularCall

CODE = """\
module shelf(width, depth, thickness=3) {
    cube([width, depth, thickness]);
    translate([0, 0, thickness])
        cube([thickness, depth, 40]);
    translate([width - thickness, 0, thickness])
        cube([thickness, depth, 40]);
}

shelf(60, 30);
translate([0, 40, 0])
    shelf(60, 30, thickness=5);
rotate([0, 0, 45])
    sphere(r = 10);
cylinder(h = 20, r = 5, center = true);
"""


def find_module_calls(nodes):
    """Yield every ModularCall node anywhere in the AST."""
    for node in nodes:
        if not isinstance(node, ASTNode):
            continue
        if isinstance(node, ModularCall):
            yield node
        for f in dataclasses.fields(node):
            if f.name in ("position", "scope"):
                continue
            val = getattr(node, f.name)
            items = val if isinstance(val, list) else [val]
            for item in items:
                yield from find_module_calls([item])


def main():
    ast = getASTfromString(CODE)

    calls = list(find_module_calls(ast))
    print(f"Found {len(calls)} module call(s):\n")

    for call in calls:
        args = ", ".join(str(a) for a in call.arguments)
        children = f"  [{len(call.children)} child(ren)]" if call.children else ""
        print(f"  line {call.position.line:3d}  {call.name}({args}){children}")


if __name__ == "__main__":
    main()
