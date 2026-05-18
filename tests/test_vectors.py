"""Tests for vectors and list comprehensions."""

import pytest
from tests.conftest import parse_success
from openscad_parser.ast import getASTfromString
from openscad_parser.ast.nodes import Assignment, ListComprehension, ListCompFor, ListCompCFor, ListCompLet


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

    def test_listcomp_each_ast(self):
        """each [1,2,3] produces ListCompEach wrapping a ListComprehension of three NumberLiterals."""
        from openscad_parser.ast import getASTfromString
        from openscad_parser.ast.nodes import (
            Assignment, ListComprehension, ListCompEach, NumberLiteral,
        )
        ast = getASTfromString("x = [each [1, 2, 3]];")
        assert len(ast) == 1
        assign = ast[0]
        assert isinstance(assign, Assignment)
        outer = assign.expr
        assert isinstance(outer, ListComprehension)
        assert len(outer.elements) == 1
        each = outer.elements[0]
        assert isinstance(each, ListCompEach)
        inner = each.body
        assert isinstance(inner, ListComprehension)
        assert len(inner.elements) == 3
        assert all(isinstance(e, NumberLiteral) for e in inner.elements)
        assert [e.val for e in inner.elements] == [1.0, 2.0, 3.0]

    def test_listcomp_each_str(self):
        """str() of each [1,2,3] renders without .0 suffixes."""
        from openscad_parser.ast import getASTfromString
        ast = getASTfromString("x = [each [1, 2, 3]];")
        assert str(ast[0].expr) == "[each [1, 2, 3]]"

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

    def test_listcomp_paren_expr_ast(self):
        """Parenthesised listcomp element (listcomp_paren_expr) builds correct AST."""
        ast = getASTfromString("x = [(for (i = [0:3]) i)];")
        assert isinstance(ast, list) and len(ast) == 1
        assign = ast[0]
        assert isinstance(assign, Assignment)
        comp = assign.expr
        assert isinstance(comp, ListComprehension)
        assert len(comp.elements) == 1
        assert isinstance(comp.elements[0], ListCompFor)


def _lc_cfor(code):
    """Parse a list-comprehension c-for from 'x = [<code>];' and return the ListCompCFor node."""
    ast = getASTfromString(f"x = [{code}];")
    node = ast[0].expr.elements[0]
    assert isinstance(node, ListCompCFor)
    return node


class TestListCompCFor:
    """Test C-style for loop list comprehension AST: inits and incrs are always list[Assignment]."""

    # --- inits counts ---

    def test_zero_inits(self):
        cfor = _lc_cfor("for ( ; i < 5 ; i = i + 1) i")
        assert cfor.inits == []
        assert isinstance(cfor.inits, list)

    def test_one_init(self):
        cfor = _lc_cfor("for (i = 0 ; i < 5 ; i = i + 1) i")
        assert len(cfor.inits) == 1
        assert isinstance(cfor.inits, list)
        assert all(isinstance(a, Assignment) for a in cfor.inits)

    def test_two_inits(self):
        cfor = _lc_cfor("for (i = 0, j = 1 ; i < 5 ; i = i + 1) i")
        assert len(cfor.inits) == 2
        assert isinstance(cfor.inits, list)
        assert all(isinstance(a, Assignment) for a in cfor.inits)

    def test_three_inits(self):
        cfor = _lc_cfor("for (i = 0, j = 1, k = 2 ; i < 5 ; i = i + 1) i")
        assert len(cfor.inits) == 3
        assert isinstance(cfor.inits, list)
        assert all(isinstance(a, Assignment) for a in cfor.inits)

    # --- incrs counts ---

    def test_zero_incrs(self):
        cfor = _lc_cfor("for (i = 0 ; i < 5 ; ) i")
        assert cfor.incrs == []
        assert isinstance(cfor.incrs, list)

    def test_one_incr(self):
        cfor = _lc_cfor("for (i = 0 ; i < 5 ; i = i + 1) i")
        assert len(cfor.incrs) == 1
        assert isinstance(cfor.incrs, list)
        assert all(isinstance(a, Assignment) for a in cfor.incrs)

    def test_two_incrs(self):
        cfor = _lc_cfor("for (i = 0 ; i < 5 ; i = i + 1, j = i * 2) i")
        assert len(cfor.incrs) == 2
        assert isinstance(cfor.incrs, list)
        assert all(isinstance(a, Assignment) for a in cfor.incrs)

    def test_three_incrs(self):
        cfor = _lc_cfor("for (i = 0 ; i < 5 ; i = i + 1, j = i * 2, k = 3) i")
        assert len(cfor.incrs) == 3
        assert isinstance(cfor.incrs, list)
        assert all(isinstance(a, Assignment) for a in cfor.incrs)

    # --- both zero ---

    def test_both_zero(self):
        cfor = _lc_cfor("for ( ; i < 5 ; ) i")
        assert cfor.inits == []
        assert cfor.incrs == []



def _lc_for(code):
    """Parse a list-comprehension for from 'x = [<code>];' and return the ListCompFor node."""
    ast = getASTfromString(f"x = [{code}];")
    node = ast[0].expr.elements[0]
    assert isinstance(node, ListCompFor)
    return node


def _lc_let(code):
    """Parse a list-comprehension let from 'x = [<code>];' and return the ListCompLet node."""
    ast = getASTfromString(f"x = [{code}];")
    node = ast[0].expr.elements[0]
    assert isinstance(node, ListCompLet)
    return node


class TestListCompFor:
    """Test ListCompFor.assignments is always list[Assignment]."""

    def test_one_assignment(self):
        lc = _lc_for("for (i = [0:5]) i")
        assert len(lc.assignments) == 1
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)

    def test_two_assignments(self):
        lc = _lc_for("for (i = [0:5], j = [0:3]) i + j")
        assert len(lc.assignments) == 2
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)

    def test_three_assignments(self):
        lc = _lc_for("for (i = [0:5], j = [0:3], k = [0:2]) i + j + k")
        assert len(lc.assignments) == 3
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)


class TestListCompLet:
    """Test ListCompLet.assignments is always list[Assignment]."""

    def test_one_assignment(self):
        lc = _lc_let("let(a = 1) for (i = [0:3]) a + i")
        assert len(lc.assignments) == 1
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)

    def test_two_assignments(self):
        lc = _lc_let("let(a = 1, b = 2) for (i = [0:3]) a + b + i")
        assert len(lc.assignments) == 2
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)

    def test_three_assignments(self):
        lc = _lc_let("let(a = 1, b = 2, c = 3) for (i = [0:3]) a + b + c + i")
        assert len(lc.assignments) == 3
        assert isinstance(lc.assignments, list)
        assert all(isinstance(a, Assignment) for a in lc.assignments)


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


