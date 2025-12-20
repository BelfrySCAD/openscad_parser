"""Tests for assignments and statements."""

import pytest
from tests.conftest import parse_success


class TestAssignments:
    """Test assignment statement parsing."""

    def test_simple_assignment(self, parser):
        """Test simple assignment."""
        code = "x = 1;"
        parse_success(parser, code)

    def test_assignment_with_expression(self, parser):
        """Test assignment with expression."""
        code = "x = 1 + 2;"
        parse_success(parser, code)

    def test_multiple_assignments(self, parser):
        """Test multiple assignments."""
        code = "x = 1; y = 2; z = 3;"
        parse_success(parser, code)

    def test_assignment_in_block(self, parser):
        """Test assignment in block."""
        code = "{ x = 1; y = 2; }"
        parse_success(parser, code)

    def test_assignment_in_module(self, parser):
        """Test assignment in module."""
        code = "module test() { x = 1; }"
        parse_success(parser, code)


class TestStatements:
    """Test statement parsing."""

    def test_empty_statement(self, parser):
        """Test empty statement."""
        code = ";"
        parse_success(parser, code)

    def test_multiple_empty_statements(self, parser):
        """Test multiple empty statements."""
        code = ";;;"
        parse_success(parser, code)

    def test_block_statement(self, parser):
        """Test block statement."""
        code = "{}"
        parse_success(parser, code)

    def test_block_with_statements(self, parser):
        """Test block with statements."""
        code = "{ x = 1; y = 2; }"
        parse_success(parser, code)

    def test_nested_blocks(self, parser):
        """Test nested blocks."""
        code = "{ { x = 1; } }"
        parse_success(parser, code)


class TestParameterLists:
    """Test parameter list parsing."""

    def test_empty_parameters(self, parser):
        """Test empty parameter list."""
        code = "module test() {}"
        parse_success(parser, code)

    def test_parameters_trailing_comma(self, parser):
        """Test parameters with trailing comma."""
        code = "module test(x, y,) {}"
        parse_success(parser, code)


class TestArgumentLists:
    """Test argument list parsing."""

    def test_empty_arguments(self, parser):
        """Test empty argument list."""
        code = "test();"
        parse_success(parser, code)

    def test_arguments_trailing_comma(self, parser):
        """Test arguments with trailing comma."""
        code = "test(1, 2,);"
        parse_success(parser, code)

    def test_arguments_named(self, parser):
        """Test named arguments."""
        code = "test(x=1, y=2);"
        parse_success(parser, code)

    def test_arguments_mixed(self, parser):
        """Test mixed positional and named arguments."""
        code = "test(1, y=2);"
        parse_success(parser, code)


class TestAssignmentExpressions:
    """Test assignment expressions (in for loops, etc.)."""

    def test_assignment_expr_simple(self, parser):
        """Test simple assignment expression."""
        code = "for (i = 0) cube(1);"
        parse_success(parser, code)

    def test_assignment_expr_multiple(self, parser):
        """Test multiple assignment expressions."""
        code = "for (i = 0, j = 1) cube(1);"
        parse_success(parser, code)

    def test_assignment_expr_in_let(self, parser):
        """Test assignment expression in let."""
        code = "let(x = 1, y = 2) cube(1);"
        parse_success(parser, code)


