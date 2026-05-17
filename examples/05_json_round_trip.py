"""JSON round-trip: serialize an AST to JSON and deserialize it back."""

import json
from openscad_parser.ast import getASTfromString, ast_to_json, ast_from_json
from openscad_parser.ast.nodes import Assignment, ModularCall, FunctionDeclaration

CODE = """\
size = 42;
function double(x) = x * 2;
cube([size, size, size]);
translate([size, 0, 0]) sphere(r = size / 2);
"""


def summarize(ast):
    return [(type(n).__name__, getattr(getattr(n, "name", None), "name", None)) for n in ast]


def main():
    ast = getASTfromString(CODE)

    print("Original AST:")
    for node in ast:
        name = getattr(getattr(node, "name", None), "name", None)
        print(f"  {type(node).__name__}" + (f" '{name}'" if name else ""))

    json_str = ast_to_json(ast, indent=2)

    parsed = json.loads(json_str)
    print(f"\nJSON: {len(json_str)} bytes, {len(parsed)} top-level entries")

    # Show first entry to illustrate the structure
    print("\nFirst JSON entry (excerpt):")
    first = parsed[0]
    print(f"  _type    : {first['_type']}")
    print(f"  _position: line {first['_position']['line']}, col {first['_position']['column']}")
    for key in first:
        if key not in ("_type", "_position"):
            print(f"  {key}: {str(first[key])[:60]}")

    restored = ast_from_json(json_str)

    print(f"\nRestored AST ({len(restored)} nodes):")
    for node in restored:
        name = getattr(getattr(node, "name", None), "name", None)
        print(f"  {type(node).__name__}" + (f" '{name}'" if name else ""))

    assert summarize(ast) == summarize(restored), "Round-trip mismatch!"
    print("\nRound-trip verified.")


if __name__ == "__main__":
    main()
