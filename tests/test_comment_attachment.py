"""include_comments=True attaches comments after a comment-free parse, so a
comment may sit anywhere whitespace may. Each case must parse, print code
that reparses, keep every comment, and print identically a second time."""
import re

import pytest

from openscad_parser.ast import getASTfromString
from openscad_parser.ast.pretty_print import to_openscad

COMMENT = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:[^"\\]|\\[\s\S])*"')


def _comments(code):
    return sorted(m.group(0).strip() for m in COMMENT.finditer(code) if not m.group(0).startswith('"'))


@pytest.mark.parametrize("src", [
    # Each failed to parse, or lost its comment, under the old comment grammar.
    "x = [0 : // why\n 2];",
    "x = let(a = 1, // c\n b = 2) a;",
    "for (i = [0:2], // c\n j = [0:1]) cube(i);",
    "translate([1, 2, 3]) // t\ncube(1);",
    "x = a ? ( // after paren\n b) : c;",
    "x = a\n  ? b // then\n  : c; // else",
    "x = [for (i = [0:2]) each if (i > 0) // only positive\n [i]];",
    "x = f(a) /* span */ + g(b);",
    "module m() {\n  // group 1\n\n  // group 2\n  cube(1);\n}",
    "x = y  // first\n  // second\n  + 1;",
])
def test_round_trip(src):
    ast = getASTfromString(src, include_comments=True)
    assert ast is not None
    out = to_openscad(ast)
    again = getASTfromString(out, include_comments=True)
    assert again is not None, out
    assert _comments(out) == _comments(src)
    assert to_openscad(again) == out
    # And it is still the same program.
    assert to_openscad(getASTfromString(out)) == to_openscad(getASTfromString(src))
