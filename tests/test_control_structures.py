"""Tests for control structures: if/else, for, let, assert, echo."""

import pytest
from tests.conftest import parse_success


class TestIfElse:
    """Test if/else statement parsing."""

    def test_if_simple(self, parser):
        """Test simple if statement."""
        code = "if (true) cube(10);"
        parse_success(parser, code)

    def test_if_with_block(self, parser):
        """Test if with block statement."""
        code = "if (true) { cube(10); }"
        parse_success(parser, code)

    def test_if_else(self, parser):
        """Test if-else statement."""
        code = "if (true) cube(10); else sphere(5);"
        parse_success(parser, code)

    def test_if_else_with_blocks(self, parser):
        """Test if-else with blocks."""
        code = "if (true) { cube(10); } else { sphere(5); }"
        parse_success(parser, code)

    def test_if_nested(self, parser):
        """Test nested if statements."""
        code = "if (true) if (false) cube(10); else sphere(5);"
        parse_success(parser, code)

    def test_if_with_expression(self, parser):
        """Test if with complex expression."""
        code = "if (x > 0 && y < 10) cube(10);"
        parse_success(parser, code)


class TestFor:
    """Test for loop parsing."""

    def test_for_range(self, parser):
        """Test for loop with range."""
        code = "for (i = [0:5]) translate([i, 0, 0]) cube(1);"
        parse_success(parser, code)

    def test_for_range_with_step(self, parser):
        """Test for loop with range and step."""
        code = "for (i = [0:2:10]) translate([i, 0, 0]) cube(1);"
        parse_success(parser, code)

    def test_for_vector(self, parser):
        """Test for loop with vector."""
        code = "for (i = [1, 2, 3]) translate([i, 0, 0]) cube(1);"
        parse_success(parser, code)

    def test_for_multiple_vars(self, parser):
        """Test for loop with multiple variables."""
        code = "for (i = [0:5], j = [0:3]) translate([i, j, 0]) cube(1);"
        parse_success(parser, code)

    def test_for_with_block(self, parser):
        """Test for loop with block."""
        code = "for (i = [0:5]) { translate([i, 0, 0]) cube(1); }"
        parse_success(parser, code)

    def test_for_c_style(self, parser):
        """Test C-style for loop."""
        code = "for (i = 0; i < 10; i = i + 1) cube(1);"
        parse_success(parser, code)

    def test_for_c_style_with_block(self, parser):
        """Test C-style for loop with block."""
        code = "for (i = 0; i < 10; i = i + 1) { cube(1); }"
        parse_success(parser, code)


class TestIntersectionFor:
    """Test intersection_for parsing."""

    def test_intersection_for_simple(self, parser):
        """Test simple intersection_for."""
        code = "intersection_for(i = [0:5]) translate([i, 0, 0]) cube(1);"
        parse_success(parser, code)

    def test_intersection_for_with_block(self, parser):
        """Test intersection_for with block."""
        code = "intersection_for(i = [0:5]) { translate([i, 0, 0]) cube(1); }"
        parse_success(parser, code)

    def test_intersection_for_multiple_vars(self, parser):
        """Test intersection_for with multiple variables."""
        code = "intersection_for(i = [0:5], j = [0:3]) translate([i, j, 0]) cube(1);"
        parse_success(parser, code)


class TestLet:
    """Test let statement parsing."""

    def test_let_simple(self, parser):
        """Test simple let statement."""
        code = "let(x = 10) cube(x);"
        parse_success(parser, code)

    def test_let_multiple(self, parser):
        """Test let with multiple assignments."""
        code = "let(x = 10, y = 20) cube([x, y, 10]);"
        parse_success(parser, code)

    def test_let_with_block(self, parser):
        """Test let with block."""
        code = "let(x = 10) { cube(x); }"
        parse_success(parser, code)

    def test_let_nested(self, parser):
        """Test nested let statements."""
        code = "let(x = 10) let(y = x * 2) cube(y);"
        parse_success(parser, code)


class TestAssert:
    """Test assert statement parsing."""

    def test_assert_simple(self, parser):
        """Test simple assert statement."""
        code = "assert(true) cube(10);"
        parse_success(parser, code)

    def test_assert_with_message(self, parser):
        """Test assert with message."""
        code = 'assert(true, "Error message") cube(10);'
        parse_success(parser, code)

    def test_assert_with_block(self, parser):
        """Test assert with block."""
        code = "assert(true) { cube(10); }"
        parse_success(parser, code)

    def test_assert_expression(self, parser):
        """Test assert in expression context."""
        code = 'x = assert(true, "error") 10;'
        parse_success(parser, code)


class TestEcho:
    """Test echo statement parsing."""

    def test_echo_simple(self, parser):
        """Test simple echo statement."""
        code = "echo(\"Hello\") cube(10);"
        parse_success(parser, code)

    def test_echo_multiple_args(self, parser):
        """Test echo with multiple arguments."""
        code = "echo(\"Hello\", \"World\") cube(10);"
        parse_success(parser, code)

    def test_echo_with_block(self, parser):
        """Test echo with block."""
        code = "echo(\"Hello\") { cube(10); }"
        parse_success(parser, code)

    def test_echo_expression(self, parser):
        """Test echo in expression context."""
        code = "x = echo(\"debug\") 10;"
        parse_success(parser, code)


class TestEach:
    """Test each keyword parsing."""

    def test_each_in_listcomp(self, parser):
        """Test each in list comprehension."""
        code = "x = [each [1, 2, 3]];"
        parse_success(parser, code)

    def test_each_nested(self, parser):
        """Test nested each."""
        code = "x = [each [each [1, 2, 3]]];"
        parse_success(parser, code)


