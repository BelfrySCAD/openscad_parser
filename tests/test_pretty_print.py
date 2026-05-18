"""Tests for the OpenSCAD pretty-printer."""

import pytest
from openscad_parser.ast import getASTfromString, to_openscad
from openscad_parser.ast.nodes import (
    Assignment, FunctionDeclaration, ModuleDeclaration,
    ModularCall, ModularFor, ModularIf, ModularIfElse,
)
from openscad_parser.ast.pretty_print import _as_list


def _roundtrip(code: str) -> list:
    """Parse → pretty-print → re-parse; return the re-parsed AST."""
    ast = getASTfromString(code)
    formatted = to_openscad(ast)
    return getASTfromString(formatted)


def _fmt(code: str) -> str:
    return to_openscad(getASTfromString(code))


class TestAssignmentFormatting:
    def test_simple_assignment(self):
        out = _fmt("x=1;")
        assert out == "x = 1.0;"

    def test_string_assignment(self):
        out = _fmt('label="hello";')
        assert out == 'label = "hello";'

    def test_bool_assignment(self):
        assert _fmt("centered=true;") == "centered = True;"

    def test_expression_assignment(self):
        out = _fmt("v=1+2;")
        assert out == "v = 1.0 + 2.0;"


class TestFunctionFormatting:
    def test_simple_function(self):
        out = _fmt("function f(x)=x*2;")
        assert out.startswith("function f(x) = ")
        assert out.endswith(";")

    def test_function_with_default(self):
        out = _fmt("function f(x=1,y=2)=x+y;")
        assert "x = 1.0" in out
        assert "y = 2.0" in out

    def test_function_roundtrip(self):
        code = "function area(w, h) = w * h;"
        ast2 = _roundtrip(code)
        assert len(ast2) == 1
        assert isinstance(ast2[0], FunctionDeclaration)
        assert ast2[0].name.name == "area"


class TestModuleFormatting:
    def test_empty_module(self):
        out = _fmt("module m(){}")
        assert "module m()" in out
        assert "{}" in out

    def test_module_with_body(self):
        out = _fmt("module box(w,h){cube([w,h,1]);}")
        assert "module box(w, h)" in out
        assert "cube(" in out

    def test_module_indentation(self):
        out = _fmt("module m(){cube(1);sphere(2);}")
        lines = out.split("\n")
        body_lines = [l for l in lines if "cube" in l or "sphere" in l]
        assert all(l.startswith("    ") for l in body_lines)

    def test_module_roundtrip(self):
        code = "module box(w=10, h=5) { cube([w, h, 1]); }"
        ast2 = _roundtrip(code)
        assert len(ast2) == 1
        assert isinstance(ast2[0], ModuleDeclaration)
        assert ast2[0].name.name == "box"
        assert len(ast2[0].parameters) == 2


class TestModuleCallFormatting:
    def test_leaf_call(self):
        out = _fmt("cube(10);")
        assert out == "cube(10.0);"

    def test_call_with_named_args(self):
        out = _fmt("cube(size=10,center=true);")
        assert "size=10.0" in out
        assert "center=True" in out

    def test_single_child_inline(self):
        out = _fmt("translate([1,2,3]) cube(10);")
        assert "translate(" in out
        assert "cube(10.0);" in out

    def test_multiple_children_block(self):
        out = _fmt("union() { cube(1); sphere(2); }")
        assert "union()" in out
        assert " {\n" in out
        assert "cube(1.0);" in out
        assert "sphere(2.0);" in out

    def test_roundtrip_nested_calls(self):
        code = "translate([1, 0, 0]) rotate([0, 0, 45]) cube(5);"
        ast2 = _roundtrip(code)
        assert len(ast2) == 1


class TestFormatting:
    def test_for_loop(self):
        out = _fmt("for(i=[0:5]) cube(i);")
        assert out.startswith("for (")
        assert "cube(" in out

    def test_for_loop_block(self):
        out = _fmt("for(i=[0:5]){cube(i);sphere(i);}")
        assert "for (" in out
        assert " {\n" in out

    def test_for_roundtrip(self):
        code = "for (i = [0:3]) cube(i);"
        ast2 = _roundtrip(code)
        assert isinstance(ast2[0], ModularFor)


class TestIfFormatting:
    def test_if_simple(self):
        out = _fmt("if(true) cube(1);")
        assert out.startswith("if (")
        assert "cube(1.0);" in out

    def test_if_else_inline(self):
        out = _fmt("if(x>0) cube(1); else sphere(2);")
        assert "if (" in out
        assert "else" in out

    def test_if_else_block(self):
        out = _fmt("if(x>0){cube(1);sphere(2);}else{cylinder(3);}")
        assert "if (" in out
        assert "else" in out

    def test_if_roundtrip(self):
        code = "if (true) cube(1); else sphere(2);"
        ast2 = _roundtrip(code)
        assert isinstance(ast2[0], ModularIfElse)


class TestModifierFormatting:
    def test_show_only(self):
        out = _fmt("!cube(1);")
        assert "!cube(1.0);" in out

    def test_highlight(self):
        out = _fmt("#cube(1);")
        assert "#cube(1.0);" in out

    def test_background(self):
        out = _fmt("%cube(1);")
        assert "%cube(1.0);" in out

    def test_disable(self):
        out = _fmt("*cube(1);")
        assert "*cube(1.0);" in out

    def test_nested_modifiers(self):
        out = _fmt("!#cube(1);")
        assert "!" in out and "#" in out and "cube" in out


class TestUseIncludeFormatting:
    def test_use(self):
        assert _fmt("use <lib.scad>") == "use <lib.scad>"

    def test_include(self):
        out = _fmt("include <lib/utils.scad>")
        assert out == "include <lib/utils.scad>"


class TestCommentFormatting:
    def test_line_comment(self):
        ast = getASTfromString("// hello\nx=1;", include_comments=True)
        out = to_openscad(ast)
        assert "// hello" in out
        assert "x = 1.0;" in out

    def test_block_comment(self):
        ast = getASTfromString("/* block */\nx=1;", include_comments=True)
        out = to_openscad(ast)
        assert "/* block */" in out


class TestBlankLineSeparation:
    def test_blank_line_before_function(self):
        out = _fmt("x=1;\nfunction f(x)=x;")
        assert "\n\n" in out

    def test_blank_line_before_module(self):
        out = _fmt("x=1;\nmodule m(){}")
        assert "\n\n" in out

    def test_blank_line_between_modules(self):
        out = _fmt("module a(){}\nmodule b(){}")
        assert "\n\n" in out

    def test_no_blank_line_between_assignments(self):
        out = _fmt("x=1;\ny=2;")
        assert "\n\n" not in out


class TestIndentWidth:
    def test_custom_indent(self):
        ast = getASTfromString("module m(){cube(1);}")
        out = to_openscad(ast, indent_width=2)
        assert "  cube(1.0);" in out

    def test_zero_indent(self):
        ast = getASTfromString("module m(){cube(1);}")
        out = to_openscad(ast, indent_width=0)
        assert "cube(1.0);" in out


class TestRoundTrip:
    """End-to-end round-trip: parse → format → re-parse, check structure preserved."""

    def test_complex_model(self):
        code = """
module shelf(width=60, depth=30, thickness=3) {
    cube([width, depth, thickness]);
    translate([0, 0, thickness])
        cube([thickness, depth, 40]);
}

function vol(w, d, t) = w * d * t;

shelf(width=80);
"""
        ast1 = getASTfromString(code.strip())
        formatted = to_openscad(ast1)
        ast2 = getASTfromString(formatted)

        assert len(ast1) == len(ast2)
        for n1, n2 in zip(ast1, ast2):
            assert type(n1) is type(n2)

    def test_for_with_if(self):
        code = "for (i = [0:10]) if (i % 2 == 0) cube(i);"
        ast2 = _roundtrip(code)
        assert isinstance(ast2[0], ModularFor)

    def test_nested_modules(self):
        code = """
module outer(n) {
    for (i = [0:n]) {
        translate([i, 0, 0]) sphere(1);
    }
}
"""
        ast2 = _roundtrip(code.strip())
        assert isinstance(ast2[0], ModuleDeclaration)
        assert ast2[0].name.name == "outer"


class TestIntersectionForFormatting:
    def test_intersection_for(self):
        out = _fmt("intersection_for(i=[0:3]) cube(i);")
        assert "intersection_for (" in out
        assert "cube(" in out

    def test_intersection_for_block(self):
        out = _fmt("intersection_for(i=[0:3]){cube(i);sphere(i);}")
        assert "intersection_for (" in out
        assert " {\n" in out

    def test_intersection_for_roundtrip(self):
        from openscad_parser.ast.nodes import ModularIntersectionFor
        code = "intersection_for (i = [0:3]) cube(i);"
        ast2 = _roundtrip(code)
        assert isinstance(ast2[0], ModularIntersectionFor)


class TestLetEchoAssertFormatting:
    def test_let_statement(self):
        out = _fmt("let(x=1) cube(x);")
        assert "let (x = 1.0)" in out
        assert "cube(x);" in out

    def test_let_block(self):
        out = _fmt("let(x=1){cube(x);sphere(x);}")
        assert "let (" in out
        assert " {\n" in out

    def test_echo_statement(self):
        out = _fmt('echo("hello") cube(1);')
        assert 'echo("hello")' in out

    def test_echo_no_child(self):
        out = _fmt('echo("debug");')
        assert 'echo("debug")' in out

    def test_assert_statement(self):
        out = _fmt("assert(true) cube(1);")
        assert "assert(True)" in out

    def test_assert_no_child(self):
        out = _fmt("assert(x > 0);")
        assert "assert(x > 0.0)" in out


class TestAsListHelper:
    def test_list_passthrough(self):
        lst = [1, 2, 3]
        assert _as_list(lst) is lst

    def test_none_returns_empty(self):
        assert _as_list(None) == []

    def test_single_value_wraps(self):
        assert _as_list("x") == ["x"]
        assert _as_list(42) == [42]
