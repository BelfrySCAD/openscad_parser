"""Tests for expressions and operator precedence."""

import pytest
from tests.conftest import parse_success


class TestArithmeticOperators:
    """Test arithmetic operator parsing."""

    def test_addition(self, parser):
        """Test addition."""
        code = "x = 1 + 2;"
        parse_success(parser, code)

    def test_subtraction(self, parser):
        """Test subtraction."""
        code = "x = 5 - 3;"
        parse_success(parser, code)

    def test_multiplication(self, parser):
        """Test multiplication."""
        code = "x = 2 * 3;"
        parse_success(parser, code)

    def test_division(self, parser):
        """Test division."""
        code = "x = 10 / 2;"
        parse_success(parser, code)

    def test_modulo(self, parser):
        """Test modulo."""
        code = "x = 10 % 3;"
        parse_success(parser, code)

    def test_exponentiation(self, parser):
        """Test exponentiation."""
        code = "x = 2 ^ 3;"
        parse_success(parser, code)

    def test_chained_operations(self, parser):
        """Test chained arithmetic operations."""
        code = "x = 1 + 2 + 3;"
        parse_success(parser, code)

    def test_mixed_operations(self, parser):
        """Test mixed arithmetic operations."""
        code = "x = 1 + 2 * 3;"
        parse_success(parser, code)


class TestOperatorPrecedence:
    """Test operator precedence."""

    def test_multiplication_before_addition(self, parser):
        """Test multiplication precedence over addition."""
        code = "x = 1 + 2 * 3;"
        parse_success(parser, code)

    def test_exponentiation_before_multiplication(self, parser):
        """Test exponentiation precedence."""
        code = "x = 2 * 3 ^ 2;"
        parse_success(parser, code)

    def test_parentheses(self, parser):
        """Test parentheses for precedence."""
        code = "x = (1 + 2) * 3;"
        parse_success(parser, code)

    def test_nested_parentheses(self, parser):
        """Test nested parentheses."""
        code = "x = ((1 + 2) * 3) / 4;"
        parse_success(parser, code)


class TestComparisonOperators:
    """Test comparison operator parsing."""

    def test_less_than(self, parser):
        """Test less than."""
        code = "x = 1 < 2;"
        parse_success(parser, code)

    def test_greater_than(self, parser):
        """Test greater than."""
        code = "x = 2 > 1;"
        parse_success(parser, code)

    def test_less_equal(self, parser):
        """Test less than or equal."""
        code = "x = 1 <= 2;"
        parse_success(parser, code)

    def test_greater_equal(self, parser):
        """Test greater than or equal."""
        code = "x = 2 >= 1;"
        parse_success(parser, code)

    def test_equal(self, parser):
        """Test equality."""
        code = "x = 1 == 2;"
        parse_success(parser, code)

    def test_not_equal(self, parser):
        """Test not equal."""
        code = "x = 1 != 2;"
        parse_success(parser, code)


class TestLogicalOperators:
    """Test logical operator parsing."""

    def test_logical_and(self, parser):
        """Test logical AND."""
        code = "x = true && false;"
        parse_success(parser, code)

    def test_logical_or(self, parser):
        """Test logical OR."""
        code = "x = true || false;"
        parse_success(parser, code)

    def test_logical_not(self, parser):
        """Test logical NOT."""
        code = "x = !true;"
        parse_success(parser, code)

    def test_logical_precedence(self, parser):
        """Test logical operator precedence."""
        code = "x = true && false || true;"
        parse_success(parser, code)


class TestUnaryOperators:
    """Test unary operator parsing."""

    def test_unary_plus(self, parser):
        """Test unary plus."""
        code = "x = +5;"
        parse_success(parser, code)

    def test_unary_minus(self, parser):
        """Test unary minus."""
        code = "x = -5;"
        parse_success(parser, code)

    def test_unary_not(self, parser):
        """Test unary NOT."""
        code = "x = !true;"
        parse_success(parser, code)

    def test_multiple_unary(self, parser):
        """Test multiple unary operators."""
        code = "x = --5;"
        parse_success(parser, code)

    def test_unary_with_expression(self, parser):
        """Test unary with expression."""
        code = "x = -(1 + 2);"
        parse_success(parser, code)


class TestBinaryBitwiseOperators:
    """Test binary bitwise operator parsing."""

    def test_binary_shift_left(self, parser):
        """Test binary shift left operator."""
        code = "x = 1 << 2;"
        parse_success(parser, code)

    def test_binary_shift_right(self, parser):
        """Test binary shift right operator."""
        code = "x = 8 >> 2;"
        parse_success(parser, code)

    def test_binary_shift_left_chained(self, parser):
        """Test chained binary shift left operations."""
        code = "x = 1 << 2 << 3;"
        parse_success(parser, code)

    def test_binary_shift_right_chained(self, parser):
        """Test chained binary shift right operations."""
        code = "x = 64 >> 2 >> 1;"
        parse_success(parser, code)

    def test_binary_shift_mixed(self, parser):
        """Test mixed shift operations."""
        code = "x = 1 << 2 >> 1;"
        parse_success(parser, code)

    def test_binary_shift_with_arithmetic(self, parser):
        """Test shift operations with arithmetic."""
        code = "x = (1 << 2) + 3;"
        parse_success(parser, code)

    def test_binary_shift_in_expression(self, parser):
        """Test shift operations in complex expressions."""
        code = "x = a << b >> c;"
        parse_success(parser, code)

    def test_binary_not(self, parser):
        """Test binary not operator."""
        code = "x = ~5;"
        parse_success(parser, code)

    def test_binary_not_with_expression(self, parser):
        """Test binary not with expression."""
        code = "x = ~(1 + 2);"
        parse_success(parser, code)

    def test_binary_not_chained(self, parser):
        """Test chained binary not operations."""
        code = "x = ~~5;"
        parse_success(parser, code)

    def test_binary_not_with_shift(self, parser):
        """Test binary not with shift operations."""
        code = "x = ~(1 << 2);"
        parse_success(parser, code)


class TestTernaryOperator:
    """Test ternary operator parsing."""

    def test_ternary_simple(self, parser):
        """Test simple ternary."""
        code = "x = true ? 1 : 2;"
        parse_success(parser, code)

    def test_ternary_nested(self, parser):
        """Test nested ternary."""
        code = "x = true ? (false ? 1 : 2) : 3;"
        parse_success(parser, code)

    def test_ternary_in_expression(self, parser):
        """Test ternary in expression."""
        code = "x = (true ? 1 : 2) * 3;"
        parse_success(parser, code)


class TestMemberAccess:
    """Test member access parsing."""

    def test_member_access(self, parser):
        """Test member access."""
        code = "x = obj.member;"
        parse_success(parser, code)

    def test_member_access_chained(self, parser):
        """Test chained member access."""
        code = "x = obj.member.submember;"
        parse_success(parser, code)

    def test_member_access_in_expression(self, parser):
        """Test member access in expression."""
        code = "x = obj.member + 1;"
        parse_success(parser, code)


class TestArrayAccess:
    """Test array access parsing."""

    def test_array_access(self, parser):
        """Test array access."""
        code = "x = arr[0];"
        parse_success(parser, code)

    def test_array_access_nested(self, parser):
        """Test nested array access."""
        code = "x = arr[0][1];"
        parse_success(parser, code)

    def test_array_access_expression(self, parser):
        """Test array access with expression."""
        code = "x = arr[i + 1];"
        parse_success(parser, code)


class TestFunctionCallInExpression:
    """Test function calls in expressions."""

    def test_function_call(self, parser):
        """Test function call."""
        code = "x = sin(0);"
        parse_success(parser, code)

    def test_function_call_nested(self, parser):
        """Test nested function calls."""
        code = "x = sin(cos(0));"
        parse_success(parser, code)

    def test_function_call_in_expression(self, parser):
        """Test function call in expression."""
        code = "x = sin(0) + cos(0);"
        parse_success(parser, code)

    def test_function_call_with_member(self, parser):
        """Test function call with member access."""
        code = "x = obj.func(1, 2);"
        parse_success(parser, code)


class TestComplexExpressions:
    """Test complex expression combinations."""

    def test_complex_expression_1(self, parser):
        """Test complex expression."""
        code = "x = (a + b) * (c - d) / (e % f);"
        parse_success(parser, code)

    def test_complex_expression_2(self, parser):
        """Test complex expression with comparisons."""
        code = "x = a > b && c < d || e == f;"
        parse_success(parser, code)

    def test_complex_expression_3(self, parser):
        """Test complex expression with function calls."""
        code = "x = sin(a) * cos(b) + tan(c);"
        parse_success(parser, code)

    def test_complex_expression_4(self, parser):
        """Test complex expression with array access."""
        code = "x = arr[i] + arr[j] * arr[k];"
        parse_success(parser, code)

    def test_complex_expression_5(self, parser):
        """Test complex expression with ternary."""
        code = "x = a > b ? c + d : e - f;"
        parse_success(parser, code)


