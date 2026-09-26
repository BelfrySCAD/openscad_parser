"""Which comma forms parse: each checked against OpenSCAD 2026.02.01 (exit
status of `openscad -o x.echo`). A list may be empty or end in one comma
after at least one item; a comma on its own is never a list."""
import pytest

from openscad_parser.ast import getASTfromString

PRELUDE = "module g() {}\nfunction f() = 1;\n"

ACCEPTED = [
    "x = [1,];", "x = [1, 2,];", "cube(1,);", "module m(a,) {}", "x = function(a,) 1;",
    "x = [for (i=[0:1]) i,];", "module m() {}", "x = [];", "x = f();", "x = let() 1;", "for () cube(1);",
]
REJECTED = [
    "g(,);", "cube(,);", "x = [,];", "module m2(,) {}", "function h(,) = 1;", "x = let(,) 1;",
    "for (,) cube(1);", "x = f(,);", "x = f(1,,);", "x = [1,,];", "x = [for (,) 1];",
    "intersection_for(,) cube(1);", "echo(,);", "assert(,);", "x = echo(,) 1;", "x = function(,) 1;",
    "module m(a,,) {}", "module m(a,,b) {}", "function f2(a,,) = 1;", "x = function(a,,) 1;",
]


@pytest.mark.parametrize("src", ACCEPTED)
def test_accepted(src):
    assert getASTfromString(PRELUDE + src) is not None


@pytest.mark.parametrize("src", REJECTED)
def test_rejected(src, capsys):
    assert getASTfromString(PRELUDE + src) is None
