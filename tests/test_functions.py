"""Tests for function definitions and calls."""

import pytest
from tests.conftest import parse_success


class TestFunctionDefinition:
    """Test function definition parsing."""

    def test_function_no_parameters(self, parser):
        """Test function with no parameters."""
        code = "function test() = 1;"
        parse_success(parser, code)

    def test_function_single_parameter(self, parser):
        """Test function with single parameter."""
        code = "function test(x) = x;"
        parse_success(parser, code)

    def test_function_multiple_parameters(self, parser):
        """Test function with multiple parameters."""
        code = "function test(x, y, z) = x + y + z;"
        parse_success(parser, code)

    def test_function_named_parameters(self, parser):
        """Test function with named parameters."""
        code = "function test(x=1, y=2) = x + y;"
        parse_success(parser, code)

    def test_function_mixed_parameters(self, parser):
        """Test function with mixed positional and named parameters."""
        code = "function test(x, y=2, z) = x + y + z;"
        parse_success(parser, code)

    def test_function_simple_expression(self, parser):
        """Test function with simple expression."""
        code = "function add(a, b) = a + b;"
        parse_success(parser, code)

    def test_function_complex_expression(self, parser):
        """Test function with complex expression."""
        code = "function complex(x) = x * 2 + sin(x) * cos(x);"
        parse_success(parser, code)

    def test_function_ternary(self, parser):
        """Test function with ternary expression."""
        code = "function abs(x) = x >= 0 ? x : -x;"
        parse_success(parser, code)

    def test_function_with_let(self, parser):
        """Test function with let expression."""
        code = "function test(x) = let(y = x * 2) y + 1;"
        parse_success(parser, code)


class TestFunctionCall:
    """Test function call parsing."""

    def test_function_call_no_args(self, parser):
        """Test function call with no arguments."""
        code = "x = test();"
        parse_success(parser, code)

    def test_function_call_single_arg(self, parser):
        """Test function call with single argument."""
        code = "x = test(5);"
        parse_success(parser, code)

    def test_function_call_multiple_args(self, parser):
        """Test function call with multiple arguments."""
        code = "x = add(1, 2);"
        parse_success(parser, code)

    def test_function_call_named_args(self, parser):
        """Test function call with named arguments."""
        code = "x = test(x=1, y=2);"
        parse_success(parser, code)

    def test_function_call_mixed_args(self, parser):
        """Test function call with mixed arguments."""
        code = "x = test(1, y=2);"
        parse_success(parser, code)

    def test_function_call_nested(self, parser):
        """Test nested function calls."""
        code = "x = add(multiply(2, 3), 4);"
        parse_success(parser, code)

    def test_function_call_in_expression(self, parser):
        """Test function call in complex expression."""
        code = "x = add(1, 2) * 3;"
        parse_success(parser, code)


class TestFunctionLiteral:
    """Test function literal (anonymous function) parsing."""

    def test_function_literal_simple(self, parser):
        """Test simple function literal."""
        code = "x = function(x) x * 2;"
        parse_success(parser, code)

    def test_function_literal_with_params(self, parser):
        """Test function literal with parameters."""
        code = "x = function(x, y) x + y;"
        parse_success(parser, code)

    def test_function_literal_call(self, parser):
        """Test calling a function literal."""
        code = "x = function(x) x * 2 (5);"
        parse_success(parser, code)


