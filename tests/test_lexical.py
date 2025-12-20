"""Tests for lexical elements: comments, strings, numbers, identifiers."""

import pytest
from tests.conftest import parse_failure, parse_success


class TestComments:
    """Test comment parsing."""

    def test_single_line_comment(self, parser):
        """Test single-line comments."""
        code = "// This is a comment"
        parse_success(parser, code)

    def test_single_line_comment_with_code(self, parser):
        """Test single-line comment with code before it."""
        code = "x = 5; // comment"
        parse_success(parser, code)

    def test_multi_line_comment(self, parser):
        """Test multi-line comments."""
        code = "/* This is a\nmulti-line comment */"
        parse_success(parser, code)

    def test_multi_line_comment_single_line(self, parser):
        """Test multi-line comment on single line."""
        code = "/* comment */"
        parse_success(parser, code)

    def test_comments_in_expressions(self, parser):
        """Test comments within expressions."""
        code = "x = 1 + /* comment */ 2;"
        parse_success(parser, code)


class TestStrings:
    """Test string literal parsing."""

    def test_single_quoted_string_rejected(self, parser):
        """Test that single-quoted strings are rejected (OpenSCAD only supports double quotes)."""
        from tests.conftest import parse_failure
        code = "x = 'hello';"
        parse_failure(parser, code)

    def test_double_quoted_string(self, parser):
        """Test double-quoted strings."""
        code = 'x = "hello";'
        parse_success(parser, code)

    def test_string_with_escapes(self, parser):
        """Test strings with escape sequences."""
        code = 'x = "hello\\nworld";'
        parse_success(parser, code)

    def test_string_with_quotes(self, parser):
        """Test strings containing quotes."""
        code = 'x = "say \\"hello\\"";'
        parse_success(parser, code)

    def test_empty_string(self, parser):
        """Test empty strings."""
        code = 'x = "";'
        parse_success(parser, code)


class TestNumbers:
    """Test number literal parsing."""

    def test_integer(self, parser):
        """Test integer numbers."""
        code = "x = 42;"
        parse_success(parser, code)

    def test_negative_integer(self, parser):
        """Test negative integers."""
        code = "x = -42;"
        parse_success(parser, code)

    def test_positive_integer(self, parser):
        """Test explicitly positive integers."""
        code = "x = +42;"
        parse_success(parser, code)

    def test_float(self, parser):
        """Test floating point numbers."""
        code = "x = 3.14;"
        parse_success(parser, code)

    def test_float_no_leading_zero(self, parser):
        """Test floats without leading zero."""
        code = "x = .5;"
        parse_success(parser, code)

    def test_scientific_notation(self, parser):
        """Test scientific notation."""
        code = "x = 1e10;"
        parse_success(parser, code)

    def test_scientific_notation_negative(self, parser):
        """Test negative scientific notation."""
        code = "x = 1e-10;"
        parse_success(parser, code)

    def test_scientific_notation_positive(self, parser):
        """Test positive scientific notation."""
        code = "x = 1e+10;"
        parse_success(parser, code)

    def test_hexadecimal(self, parser):
        """Test hexadecimal numbers."""
        code = "x = 0xFF;"
        parse_success(parser, code)

    def test_hexadecimal_lowercase(self, parser):
        """Test lowercase hexadecimal numbers."""
        code = "x = 0xff;"
        parse_success(parser, code)


class TestIdentifiers:
    """Test identifier parsing."""

    def test_simple_identifier(self, parser):
        """Test simple identifiers."""
        code = "x = 1;"
        parse_success(parser, code)

    def test_identifier_with_underscore(self, parser):
        """Test identifiers with underscores."""
        code = "my_var = 1;"
        parse_success(parser, code)

    def test_identifier_with_numbers(self, parser):
        """Test identifiers with numbers."""
        code = "var1 = 1;"
        parse_success(parser, code)

    def test_identifier_dollar_sign(self, parser):
        """Test identifiers starting with dollar sign."""
        code = "$var = 1;"
        parse_success(parser, code)

    def test_identifier_mixed_case(self, parser):
        """Test mixed case identifiers."""
        code = "myVariable = 1;"
        parse_success(parser, code)


class TestBooleans:
    """Test boolean literal parsing."""

    def test_true(self, parser):
        """Test true boolean."""
        code = "x = true;"
        parse_success(parser, code)

    def test_false(self, parser):
        """Test false boolean."""
        code = "x = false;"
        parse_success(parser, code)

    def test_mixedcase_true_rejected(self, parser):
        """Test that mixedcase true is rejected."""
        code = "x = True;"
        parse_failure(parser, code)

    def test_mixedcase_false_rejected(self, parser):
        """Test that mixedcase false is rejected."""
        code = "x = False;"
        parse_failure(parser, code)

    def test_uppercase_true_rejected(self, parser):
        """Test that uppercase true is rejected."""
        code = "x = TRUE;"
        parse_failure(parser, code)

    def test_uppercase_false_rejected(self, parser):
        """Test that uppercase false is rejected."""
        code = "x = FALSE;"
        parse_failure(parser, code)


class TestUndef:
    """Test undef literal parsing."""

    def test_undef(self, parser):
        """Test undef literal."""
        code = "x = undef;"
        parse_success(parser, code)

    def test_mixedcase_undef_rejected(self, parser):
        """Test that mixedcase undef is rejected."""
        code = "x = UnDef;"
        parse_failure(parser, code)

    def test_uppercase_undef_rejected(self, parser):
        """Test that uppercase undef is rejected."""
        code = "x = UNDEF;"
        parse_failure(parser, code)

