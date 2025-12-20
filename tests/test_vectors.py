"""Tests for vectors and list comprehensions."""

import pytest
from tests.conftest import parse_success


class TestVectors:
    """Test vector literal parsing."""

    def test_empty_vector(self, parser):
        """Test empty vector."""
        code = "x = [];"
        parse_success(parser, code)

    def test_vector_single_element(self, parser):
        """Test vector with single element."""
        code = "x = [1];"
        parse_success(parser, code)

    def test_vector_multiple_elements(self, parser):
        """Test vector with multiple elements."""
        code = "x = [1, 2, 3];"
        parse_success(parser, code)

    def test_vector_mixed_types(self, parser):
        """Test vector with mixed types."""
        code = "x = [1, \"hello\", true];"
        parse_success(parser, code)

    def test_vector_nested(self, parser):
        """Test nested vectors."""
        code = "x = [[1, 2], [3, 4]];"
        parse_success(parser, code)

    def test_vector_with_expressions(self, parser):
        """Test vector with expressions."""
        code = "x = [1 + 2, 3 * 4, 5 / 6];"
        parse_success(parser, code)

    def test_vector_trailing_comma(self, parser):
        """Test vector with trailing comma."""
        code = "x = [1, 2, 3,];"
        parse_success(parser, code)


class TestRanges:
    """Test range syntax parsing."""

    def test_range_simple(self, parser):
        """Test simple range."""
        code = "x = [0:5];"
        parse_success(parser, code)

    def test_range_with_step(self, parser):
        """Test range with step."""
        code = "x = [0:2:10];"
        parse_success(parser, code)

    def test_range_negative(self, parser):
        """Test range with negative numbers."""
        code = "x = [-5:5];"
        parse_success(parser, code)

    def test_range_expressions(self, parser):
        """Test range with expressions."""
        code = "x = [0:2*5:10];"
        parse_success(parser, code)


class TestListComprehensionFor:
    """Test list comprehension with for."""

    def test_listcomp_for_simple(self, parser):
        """Test simple list comprehension with for."""
        code = "x = [for (i = [0:5]) i];"
        parse_success(parser, code)

    def test_listcomp_for_expression(self, parser):
        """Test list comprehension with expression."""
        code = "x = [for (i = [0:5]) i * 2];"
        parse_success(parser, code)

    def test_listcomp_for_c_style(self, parser):
        """Test list comprehension with C-style for."""
        code = "x = [for (i = 0; i < 10; i = i + 1) i];"
        parse_success(parser, code)

    def test_listcomp_for_multiple_vars(self, parser):
        """Test list comprehension with multiple variables."""
        code = "x = [for (i = [0:5], j = [0:3]) i + j];"
        parse_success(parser, code)

    def test_listcomp_for_nested(self, parser):
        """Test nested list comprehension."""
        code = "x = [for (i = [0:5]) [for (j = [0:3]) i + j]];"
        parse_success(parser, code)


class TestListComprehensionIf:
    """Test list comprehension with if."""

    def test_listcomp_if_simple(self, parser):
        """Test simple list comprehension with if."""
        code = "x = [for (i = [0:5]) if (i % 2 == 0) i];"
        parse_success(parser, code)

    def test_listcomp_if_else(self, parser):
        """Test list comprehension with if-else."""
        code = "x = [for (i = [0:5]) if (i % 2 == 0) i else -i];"
        parse_success(parser, code)

    def test_listcomp_if_nested(self, parser):
        """Test nested if in list comprehension."""
        code = "x = [for (i = [0:5]) if (i > 0) if (i < 5) i];"
        parse_success(parser, code)


class TestListComprehensionLet:
    """Test list comprehension with let."""

    def test_listcomp_let_simple(self, parser):
        """Test simple list comprehension with let."""
        code = "x = [for (i = [0:5]) let(j = i * 2) j];"
        parse_success(parser, code)

    def test_listcomp_let_multiple(self, parser):
        """Test list comprehension with multiple let assignments."""
        code = "x = [for (i = [0:5]) let(j = i * 2, k = j + 1) k];"
        parse_success(parser, code)

    def test_listcomp_let_nested(self, parser):
        """Test nested let in list comprehension."""
        code = "x = [for (i = [0:5]) let(j = i * 2) let(k = j + 1) k];"
        parse_success(parser, code)


class TestListComprehensionEach:
    """Test list comprehension with each."""

    def test_listcomp_each_simple(self, parser):
        """Test simple list comprehension with each."""
        code = "x = [each [1, 2, 3]];"
        parse_success(parser, code)

    def test_listcomp_each_in_for(self, parser):
        """Test each in for list comprehension."""
        code = "x = [for (i = [0:2]) each [i, i+1]];"
        parse_success(parser, code)

    def test_listcomp_each_nested(self, parser):
        """Test nested each."""
        code = "x = [each [each [1, 2, 3]]];"
        parse_success(parser, code)


class TestListComprehensionComplex:
    """Test complex list comprehension combinations."""

    def test_listcomp_for_if(self, parser):
        """Test list comprehension with for and if."""
        code = "x = [for (i = [0:10]) if (i % 2 == 0) i * 2];"
        parse_success(parser, code)

    def test_listcomp_for_let_if(self, parser):
        """Test list comprehension with for, let, and if."""
        code = "x = [for (i = [0:10]) let(j = i * 2) if (j > 5) j];"
        parse_success(parser, code)

    def test_listcomp_nested_complex(self, parser):
        """Test complex nested list comprehension."""
        code = "x = [for (i = [0:5]) [for (j = [0:3]) if (i + j > 3) i + j]];"
        parse_success(parser, code)

    def test_listcomp_parentheses(self, parser):
        """Test list comprehension with parentheses."""
        code = "x = [for (i = [0:5]) (i * 2)];"
        parse_success(parser, code)

    def test_listcomp_nested_parentheses(self, parser):
        """Test list comprehension with nested parentheses."""
        code = "x = [for (i = [0:5]) (for (j = [0:3]) i + j)];"
        parse_success(parser, code)


class TestVectorOperations:
    """Test vector operations."""

    def test_vector_assignment(self, parser):
        """Test vector assignment."""
        code = "x = [1, 2, 3];"
        parse_success(parser, code)

    def test_vector_in_function(self, parser):
        """Test vector in function call."""
        code = "cube([10, 20, 30]);"
        parse_success(parser, code)

    def test_vector_in_expression(self, parser):
        """Test vector in expression."""
        code = "x = [1, 2, 3] + [4, 5, 6];"
        parse_success(parser, code)

    def test_vector_access(self, parser):
        """Test vector element access."""
        code = "x = vec[0];"
        parse_success(parser, code)


