"""Tests for module definitions and instantiations."""

import pytest
from tests.conftest import parse_success
from openscad_parser.ast import getASTfromString
from openscad_parser.ast.nodes import ModularCall, ModularFor, ModularIf, ModularIfElse


class TestModuleDefinition:
    """Test module definition parsing."""

    def test_module_no_parameters(self, parser):
        """Test module with no parameters."""
        code = "module test() {}"
        parse_success(parser, code)

    def test_module_single_parameter(self, parser):
        """Test module with single parameter."""
        code = "module test(x) {}"
        parse_success(parser, code)

    def test_module_multiple_parameters(self, parser):
        """Test module with multiple parameters."""
        code = "module test(x, y, z) {}"
        parse_success(parser, code)

    def test_module_multiple_parameters_trailing_comma(self, parser):
        """Test parameters with trailing comma."""
        code = "module test(x, y,) {}"
        parse_success(parser, code)

    def test_module_named_parameters(self, parser):
        """Test module with named parameters."""
        code = "module test(x=1, y=2) {}"
        parse_success(parser, code)

    def test_module_mixed_parameters(self, parser):
        """Test module with mixed positional and named parameters."""
        code = "module test(x, y=2, z) {}"
        parse_success(parser, code)

    def test_module_with_body(self, parser):
        """Test module with body statements."""
        code = "module test() { cube(10); }"
        parse_success(parser, code)

    def test_module_multiple_statements(self, parser):
        """Test module with multiple statements."""
        code = "module test() { cube(10); sphere(5); }"
        parse_success(parser, code)

    def test_module_mixed_statements(self, parser):
        """Test module with mixed statements."""
        code = "module test(a, b=2) { s = 3 * a + b; cube(s); }"
        parse_success(parser, code)

    def test_module_nested(self, parser):
        """Test nested module definitions."""
        code = "module outer() { module inner() {} }"
        parse_success(parser, code)

    def test_module_with_comment(self, parser, parser_comments):
        """Test module defined with comments"""
        code = "module test() {\nsphere(5);\n// comment\ncube(10);}"
        parse_success(parser, code)
        parse_success(parser_comments, code)

class TestModuleInstantiation:
    """Test module instantiation parsing."""

    def test_module_call_no_args(self, parser):
        """Test module call with no arguments."""
        code = "cube();"
        parse_success(parser, code)

    def test_module_call_single_arg(self, parser):
        """Test module call with single argument."""
        code = "cube(10);"
        parse_success(parser, code)

    def test_module_call_multiple_args(self, parser):
        """Test module call with multiple arguments."""
        code = "cube([10, 20, 30]);"
        parse_success(parser, code)

    def test_module_call_named_args(self, parser):
        """Test module call with named arguments."""
        code = "cube(size=10);"
        parse_success(parser, code)

    def test_module_call_mixed_args(self, parser):
        """Test module call with mixed positional and named arguments."""
        code = "translate([1, 2, 3]) cube(size=10);"
        parse_success(parser, code)

    def test_module_call_chained(self, parser):
        """Test chained module calls."""
        code = "translate([1, 2, 3]) rotate([0, 0, 45]) cube(10);"
        parse_success(parser, code)


class TestModuleModifiers:
    """Test module modifier parsing."""

    def test_modifier_show_only(self, parser):
        """Test show only modifier (!)."""
        code = "!cube(10);"
        parse_success(parser, code)

    def test_modifier_highlight(self, parser):
        """Test highlight modifier (#)."""
        code = "#cube(10);"
        parse_success(parser, code)

    def test_modifier_background(self, parser):
        """Test background modifier (%)."""
        code = "%cube(10);"
        parse_success(parser, code)

    def test_modifier_disable(self, parser):
        """Test disable modifier (*)."""
        code = "*cube(10);"
        parse_success(parser, code)

    def test_modifier_nested(self, parser):
        """Test nested modifiers."""
        code = "!#cube(10);"
        parse_success(parser, code)

    def test_modifier_with_transform(self, parser):
        """Test modifier with transform."""
        code = "!translate([1, 2, 3]) cube(10);"
        parse_success(parser, code)


class TestModuleComplex:
    """Test complex module scenarios."""

    def test_module_with_variables(self, parser):
        """Test module with variable assignments."""
        code = "module test() { x = 10; cube(x); }"
        parse_success(parser, code)

    def test_module_with_conditionals(self, parser):
        """Test module with conditional statements."""
        code = "module test() { if (true) cube(10); }"
        parse_success(parser, code)

    def test_module_with_loops(self, parser):
        """Test module with for loops."""
        code = "module test() { for (i = [0:5]) translate([i, 0, 0]) cube(1); }"
        parse_success(parser, code)

    def test_module_instantiation_in_expression(self, parser):
        """Test module instantiation in expression context."""
        code = "x = cube(10);"
        # Note: This might not be valid OpenSCAD, but tests parser behavior
        parse_success(parser, code)




class TestChildStatementMultipleChildren:
    """Regression tests for issue #10: visit_child_statement dropping all but
    the first child when a statement_block contains multiple instantiations."""

    def test_modular_call_block_all_children_returned(self):
        """translate() with a block of three cubes should yield all three children."""
        code = """
translate([1, 2, 3])
    rotate([4, 5, 6]) {
        cube([7, 7, 7]);
        cube([8, 8, 8]);
        cube([9, 9, 9]);
    }
"""
        ast = getASTfromString(code)
        assert ast is not None and isinstance(ast, list)
        translate = ast[0]
        assert isinstance(translate, ModularCall)
        assert translate.name.name == "translate"

        rotate = translate.children[0]
        assert isinstance(rotate, ModularCall)
        assert rotate.name.name == "rotate"
        assert len(rotate.children) == 3, (
            f"Expected 3 children, got {len(rotate.children)}: {rotate.children}"
        )
        names = [c.name.name for c in rotate.children]
        assert names == ["cube", "cube", "cube"]

    def test_for_block_all_children_returned(self):
        """for loop with a block body should capture all child instantiations."""
        code = "for (i = [0:2]) { cube(i); sphere(i); }"
        ast = getASTfromString(code)
        assert ast is not None and isinstance(ast, list)
        for_node = ast[0]
        assert isinstance(for_node, ModularFor)
        body = for_node.body
        assert isinstance(body, list)
        assert len(body) == 2
        assert body[0].name.name == "cube"
        assert body[1].name.name == "sphere"

    def test_if_block_all_children_returned(self):
        """if statement with a block body should capture all child instantiations."""
        code = "if (true) { cube(1); sphere(2); cylinder(3); }"
        ast = getASTfromString(code)
        assert ast is not None and isinstance(ast, list)
        if_node = ast[0]
        assert isinstance(if_node, ModularIf)
        branch = if_node.true_branch
        assert isinstance(branch, list)
        assert len(branch) == 3

    def test_ifelse_block_both_branches_complete(self):
        """if/else with blocks should capture all children in each branch."""
        code = "if (true) { cube(1); sphere(2); } else { cylinder(3); cube(4); }"
        ast = getASTfromString(code)
        assert ast is not None and isinstance(ast, list)
        if_node = ast[0]
        assert isinstance(if_node, ModularIfElse)
        assert len(if_node.true_branch) == 2
        assert len(if_node.false_branch) == 2

    def test_single_child_statement_still_works(self):
        """Single child (no block) should still work and return a one-element list."""
        code = "translate([1, 0, 0]) cube(5);"
        ast = getASTfromString(code)
        assert ast is not None and isinstance(ast, list)
        translate = ast[0]
        assert isinstance(translate, ModularCall)
        assert len(translate.children) == 1
        assert translate.children[0].name.name == "cube"
