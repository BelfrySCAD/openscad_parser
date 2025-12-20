"""Tests for module definitions and instantiations."""

import pytest
from tests.conftest import parse_success


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


