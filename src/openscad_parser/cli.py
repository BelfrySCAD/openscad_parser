"""Command-line interface for openscad_parser."""
import sys
import argparse
from openscad_parser.ast import getASTfromString, getASTfromFile, ast_to_json
from openscad_parser.ast.pretty_print import to_openscad


def main():
    ap = argparse.ArgumentParser(
        prog="openscad-parser",
        description=(
            "Parse an OpenSCAD file and dump its AST as JSON (default), "
            "YAML, or reformatted OpenSCAD source."
        ),
    )
    ap.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help="OpenSCAD source file to parse. Omit or use '-' to read from stdin.",
    )
    output = ap.add_mutually_exclusive_group()
    output.add_argument(
        "--json", action="store_true", default=True,
        help="Output AST as JSON (default).",
    )
    output.add_argument(
        "--yaml", action="store_true",
        help="Output AST as YAML (requires PyYAML).",
    )
    output.add_argument(
        "--format", action="store_true",
        help="Output reformatted OpenSCAD source code.",
    )
    ap.add_argument(
        "--include-comments", action="store_true",
        help="Include comment nodes in the AST.",
    )
    ap.add_argument(
        "--no-includes", action="store_true",
        help="Do not expand include <...> statements (keeps IncludeStatement nodes).",
    )
    ap.add_argument(
        "--indent", type=int, default=4, metavar="N",
        help="Indentation width in spaces (default: 4). Applies to --format and --json.",
    )
    args = ap.parse_args()

    # --yaml and --format clear the --json default
    if args.yaml or args.format:
        args.json = False

    try:
        if args.file is None or args.file == "-":
            code = sys.stdin.read()
            ast = getASTfromString(code, include_comments=args.include_comments)
        else:
            ast = getASTfromFile(
                args.file,
                include_comments=args.include_comments,
                process_includes=not args.no_includes,
            )
    except FileNotFoundError as e:
        print(f"openscad-parser: {e}", file=sys.stderr)
        sys.exit(1)

    if ast is None:
        sys.exit(1)

    if args.format:
        print(to_openscad(ast, indent_width=args.indent))
    elif args.yaml:
        try:
            from openscad_parser.ast import ast_to_yaml
        except ImportError:  # pragma: no cover
            print("openscad-parser: --yaml requires PyYAML (pip install openscad_parser[yaml])", file=sys.stderr)
            sys.exit(1)
        print(ast_to_yaml(ast))
    else:
        print(ast_to_json(ast, indent=args.indent))


if __name__ == "__main__":  # pragma: no cover
    main()
