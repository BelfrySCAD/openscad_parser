"""Tests for AST node generation from parsed OpenSCAD code."""

import pytest
from openscad_parser import getOpenSCADParser
from openscad_parser.ast import (
    ASTBuilderVisitor,
    Identifier, StringLiteral, NumberLiteral, BooleanLiteral, UndefinedLiteral,
    RangeLiteral, CommentLine, CommentSpan,
    ParameterDeclaration, PositionalArgument, NamedArgument,
    Assignment, LetOp, EchoOp, AssertOp,
    UnaryMinusOp, AdditionOp, SubtractionOp, MultiplicationOp, DivisionOp,
    ModuloOp, ExponentOp, BitwiseAndOp, BitwiseOrOp, BitwiseNotOp,
    BitwiseShiftLeftOp, BitwiseShiftRightOp, LogicalAndOp, LogicalOrOp, LogicalNotOp,
    TernaryOp, EqualityOp, InequalityOp, GreaterThanOp, GreaterThanOrEqualOp,
    LessThanOp, LessThanOrEqualOp,
    FunctionLiteral, PrimaryCall, PrimaryIndex, PrimaryMember,
    ModuleDeclaration, FunctionDeclaration,
    UseStatement, IncludeStatement,
    ModularCall, ModularFor, ModularIntersectionFor,
    ModularLet, ModularEcho, ModularAssert,
    ModularIf, ModularIfElse,
    ModularModifierShowOnly, ModularModifierHighlight, ModularModifierBackground, ModularModifierDisable,
    ListComprehension, ListCompLet, ListCompEach, ListCompFor, ListCompCFor,
    ListCompIf, ListCompIfElse,
    Position
)


# Import the public parse_ast function from ast module
from openscad_parser.ast import parse_ast, getASTfromString


class TestLiteralASTNodes:
    """Test AST generation for literal values."""

    def test_identifier_ast(self, parser):
        """Test Identifier AST node generation."""
        code = "x = 5;"
        ast = parse_ast(parser, code)
        # Find the assignment
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.name, Identifier)
        assert assignment.name.name == "x"

    def test_string_literal_ast(self, parser):
        """Test StringLiteral AST node generation."""
        code = 'x = "hello";'
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        # The expression should be a StringLiteral
        assert isinstance(assignment.expr, StringLiteral)
        assert assignment.expr.val == "hello"

    def test_empty_string_ast(self, parser):
        """Test that an empty string produces a StringLiteral with empty val."""
        code = 'x = "";'
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, StringLiteral)
        assert assignment.expr.val == ""

    def test_string_with_leading_spaces_ast(self, parser):
        """Test that a string with leading spaces preserves those spaces in val."""
        code = 'x = "  foo";'
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, StringLiteral)
        assert assignment.expr.val == "  foo"

    def test_number_literal_ast(self, parser):
        """Test NumberLiteral AST node generation."""
        code = "x = 42;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, NumberLiteral)
        assert assignment.expr.val == 42.0

    def test_boolean_literal_ast(self, parser):
        """Test BooleanLiteral AST node generation."""
        code = "x = true; y = false;"
        ast = parse_ast(parser, code)
        assert ast is not None
        assert len(ast) >= 2
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, BooleanLiteral)
        assert ast[0].expr.val is True
        assert isinstance(ast[1], Assignment)
        assert isinstance(ast[1].expr, BooleanLiteral)
        assert ast[1].expr.val is False

    def test_undefined_literal_ast(self, parser):
        """Test UndefinedLiteral AST node generation."""
        code = "x = undef;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, UndefinedLiteral)

    def test_range_literal_ast(self, parser):
        """Test RangeLiteral AST node generation."""
        code = "x = [1:10];"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, RangeLiteral)
        assert isinstance(assignment.expr.start, NumberLiteral)
        assert assignment.expr.start.val == 1.0
        assert isinstance(assignment.expr.end, NumberLiteral)
        assert assignment.expr.end.val == 10.0
        assert isinstance(assignment.expr.step, NumberLiteral)
        assert assignment.expr.step.val == 1.0  # Default step

    def test_range_literal_with_step_ast(self, parser):
        """Test RangeLiteral with explicit step."""
        code = "x = [1:10:2];"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.expr, RangeLiteral)
        assert isinstance(assignment.expr.step, NumberLiteral)
        assert assignment.expr.step.val == 2.0


class TestCommentASTNodes:
    """Test AST generation for comments."""

    def test_comment_line_excluded_by_default(self, parser):
        """Test that single-line comments are excluded from AST by default."""
        code = "// This is a comment\nx = 5;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should only have the assignment, no comment
        assert len(ast) == 1
        assert not any(isinstance(node, CommentLine) for node in ast)
        assert not any(isinstance(node, CommentSpan) for node in ast)

    def test_comment_multi_excluded_by_default(self, parser):
        """Test that multi-line comments are excluded from AST by default."""
        code = "/* This is a\nmulti-line comment */\nx = 5;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should only have the assignment, no comment
        assert len(ast) == 1
        assert not any(isinstance(node, CommentLine) for node in ast)
        assert not any(isinstance(node, CommentSpan) for node in ast)

    def test_comment_line_included_when_requested(self):
        """Test that single-line comments are included in AST when include_comments=True."""
        from openscad_parser import getOpenSCADParser
        from openscad_parser.ast import parse_ast
        
        parser = getOpenSCADParser(reduce_tree=False, include_comments=True)
        code = "// This is a comment\nx = 5;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have both the comment and the assignment
        assert len(ast) == 2
        comment_nodes = [node for node in ast if isinstance(node, CommentLine)]
        assert len(comment_nodes) == 1
        assert comment_nodes[0].text == " This is a comment"
        # Verify assignment is still there
        assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
        assert len(assignment_nodes) == 1

    def test_comment_multi_included_when_requested(self):
        """Test that multi-line comments are included in AST when include_comments=True."""
        from openscad_parser import getOpenSCADParser
        from openscad_parser.ast import parse_ast
        
        parser = getOpenSCADParser(reduce_tree=False, include_comments=True)
        code = "/* This is a\nmulti-line comment */\nx = 5;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have both the comment and the assignment
        assert len(ast) == 2
        comment_nodes = [node for node in ast if isinstance(node, CommentSpan)]
        assert len(comment_nodes) == 1
        assert "This is a\nmulti-line comment" in comment_nodes[0].text
        # Verify assignment is still there
        assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
        assert len(assignment_nodes) == 1

    def test_multiple_comments_included(self):
        """Test that multiple comments are included when include_comments=True."""
        from openscad_parser import getOpenSCADParser
        from openscad_parser.ast import parse_ast
        
        parser = getOpenSCADParser(reduce_tree=False, include_comments=True)
        code = "// First comment\nx = 5;\n// Second comment\ny = 10;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have 2 comments and 2 assignments = 4 nodes
        assert len(ast) == 4
        comment_nodes = [node for node in ast if isinstance(node, CommentLine)]
        assert len(comment_nodes) == 2
        assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
        assert len(assignment_nodes) == 2

    def test_mixed_comment_types_included(self):
        """Test that both single-line and multi-line comments are included."""
        from openscad_parser import getOpenSCADParser
        from openscad_parser.ast import parse_ast
        
        parser = getOpenSCADParser(reduce_tree=False, include_comments=True)
        code = "// Single-line comment\n/* Multi-line\ncomment */\nx = 5;"
        ast = parse_ast(parser, code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have 2 comments and 1 assignment = 3 nodes
        assert len(ast) == 3
        line_comments = [node for node in ast if isinstance(node, CommentLine)]
        span_comments = [node for node in ast if isinstance(node, CommentSpan)]
        assert len(line_comments) == 1
        assert len(span_comments) == 1


class TestExpressionASTNodes:
    """Test AST generation for expressions."""

    def test_addition_ast(self, parser):
        """Test AdditionOp AST node generation."""
        code = "x = 1 + 2;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, AdditionOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_subtraction_ast(self, parser):
        """Test SubtractionOp AST node generation."""
        code = "x = 5 - 3;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, SubtractionOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_multiplication_ast(self, parser):
        """Test MultiplicationOp AST node generation."""
        code = "x = 2 * 3;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, MultiplicationOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_division_ast(self, parser):
        """Test DivisionOp AST node generation."""
        code = "x = 10 / 2;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, DivisionOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_modulo_ast(self, parser):
        """Test ModuloOp AST node generation."""
        code = "x = 10 % 3;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, ModuloOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_exponent_ast(self, parser):
        """Test ExponentOp AST node generation."""
        code = "x = 2 ^ 3;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, ExponentOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert isinstance(ast[0].expr.right, NumberLiteral)

    def test_unary_minus_ast(self, parser):
        """Test UnaryMinusOp AST node generation."""
        code = "x = -5;"
        ast = parse_ast(parser, code)
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, UnaryMinusOp)
        assert isinstance(ast[0].expr.expr, NumberLiteral)

    def test_logical_and_ast(self, parser):
        """Test LogicalAndOp AST node generation."""
        code = "x = true && false;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, LogicalAndOp)

    def test_logical_or_ast(self, parser):
        """Test LogicalOrOp AST node generation."""
        code = "x = true || false;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, LogicalOrOp)

    def test_logical_not_ast(self, parser):
        """Test LogicalNotOp AST node generation."""
        code = "x = !true;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, LogicalNotOp)

    def test_equality_ast(self, parser):
        """Test EqualityOp AST node generation."""
        code = "x = 1 == 2;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, EqualityOp)

    def test_inequality_ast(self, parser):
        """Test InequalityOp AST node generation."""
        code = "x = 1 != 2;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, InequalityOp)

    def test_comparison_operators_ast(self, parser):
        """Test comparison operator AST nodes."""
        test_cases = [
            ("x = 1 < 2;", LessThanOp),
            ("x = 1 > 2;", GreaterThanOp),
            ("x = 1 <= 2;", LessThanOrEqualOp),
            ("x = 1 >= 2;", GreaterThanOrEqualOp),
        ]
        for code, expected_type in test_cases:
            # Create a fresh parser for each test case to avoid memoization issues
            # when reusing the same parser instance
            fresh_parser = getOpenSCADParser(reduce_tree=False)
            ast = parse_ast(fresh_parser, code)
            assignment = ast[0] if isinstance(ast, list) else ast
            assert assignment is not None
            assert isinstance(assignment, Assignment)
            assert assignment.expr is not None
            assert isinstance(assignment.expr, expected_type), f"Failed for {code}"

    def test_ternary_ast(self, parser):
        """Test TernaryOp AST node generation."""
        code = "x = true ? 1 : 2;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, TernaryOp)
        assert isinstance(assignment.expr.condition, BooleanLiteral)
        assert isinstance(assignment.expr.true_expr, NumberLiteral)
        assert isinstance(assignment.expr.false_expr, NumberLiteral)

    def test_bitwise_operators_ast(self, parser):
        """Test bitwise operator AST nodes."""
        test_cases = [
            ("x = 1 & 2;", BitwiseAndOp),
            ("x = 1 | 2;", BitwiseOrOp),
            ("x = ~1;", BitwiseNotOp),
            ("x = 1 << 2;", BitwiseShiftLeftOp),
            ("x = 1 >> 2;", BitwiseShiftRightOp),
        ]
        for code, expected_type in test_cases:
            # Create a fresh parser for each test case to avoid memoization issues
            # when reusing the same parser instance
            fresh_parser = getOpenSCADParser(reduce_tree=False)
            ast = parse_ast(fresh_parser, code)
            assignment = ast[0] if isinstance(ast, list) else ast
            assert assignment is not None
            assert isinstance(assignment, Assignment)
            assert assignment.expr is not None
            assert isinstance(assignment.expr, expected_type), f"Failed for {code}"

    def test_operator_precedence_ast(self, parser):
        """Test that operator precedence is correctly represented in AST."""
        code = "x = 1 + 2 * 3;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        # Should be: 1 + (2 * 3)
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, AdditionOp)
        assert isinstance(assignment.expr.right, MultiplicationOp)


class TestFunctionCallASTNodes:
    """Test AST generation for function calls."""

    def test_function_call_no_arguments(self, parser):
        """Test PrimaryCall with no arguments."""
        code = "x = foo();"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert isinstance(assignment.expr.left, Identifier)
        assert assignment.expr.left.name == "foo"
        assert len(assignment.expr.arguments) == 0

    def test_function_call_one_positional_argument(self, parser):
        """Test PrimaryCall with one positional argument."""
        code = "x = foo(1);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert isinstance(assignment.expr.left, Identifier)
        assert assignment.expr.left.name == "foo"
        assert len(assignment.expr.arguments) == 1
        assert isinstance(assignment.expr.arguments[0], PositionalArgument)
        assert isinstance(assignment.expr.arguments[0].expr, NumberLiteral)
        assert assignment.expr.arguments[0].expr.val == 1

    def test_function_call_multiple_positional_arguments(self, parser):
        """Test PrimaryCall with multiple positional arguments."""
        code = "x = foo(1, 2, 3);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert isinstance(assignment.expr.left, Identifier)
        assert assignment.expr.left.name == "foo"
        assert len(assignment.expr.arguments) == 3
        for i, arg in enumerate(assignment.expr.arguments):
            assert isinstance(arg, PositionalArgument)
            assert isinstance(arg.expr, NumberLiteral)
            assert arg.expr.val == [1, 2, 3][i]

    def test_function_call_ast(self, parser):
        """Test PrimaryCall AST node generation."""
        code = "x = foo(1, 2);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert isinstance(assignment.expr.left, Identifier)
        assert assignment.expr.left.name == "foo"
        assert len(assignment.expr.arguments) == 2
        assert isinstance(assignment.expr.arguments[0], PositionalArgument)
        assert isinstance(assignment.expr.arguments[1], PositionalArgument)

    def test_function_call_named_args_ast(self, parser):
        """Test function call with named arguments."""
        code = "x = foo(a=1, b=2);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert len(assignment.expr.arguments) == 2
        assert isinstance(assignment.expr.arguments[0], NamedArgument)
        assert isinstance(assignment.expr.arguments[1], NamedArgument)
        assert isinstance(assignment.expr.arguments[0].name, Identifier)
        assert assignment.expr.arguments[0].name.name == "a"
        assert isinstance(assignment.expr.arguments[1].name, Identifier)
        assert assignment.expr.arguments[1].name.name == "b"

    def test_function_call_mixed_args_ast(self, parser):
        """Test function call with mixed positional and named arguments."""
        code = "x = foo(1, b=2);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None   
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryCall)
        assert len(assignment.expr.arguments) == 2
        assert isinstance(assignment.expr.arguments[0], PositionalArgument)
        assert isinstance(assignment.expr.arguments[1], NamedArgument)
        assert isinstance(assignment.expr.arguments[1].name, Identifier)
        assert assignment.expr.arguments[1].name.name == "b"

    def test_index_access_ast(self, parser):
        """Test PrimaryIndex AST node generation."""
        code = "x = arr[0];"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryIndex)
        assert isinstance(assignment.expr.left, Identifier)
        assert isinstance(assignment.expr.index, NumberLiteral)

    def test_member_access_ast(self, parser):
        """Test PrimaryMember AST node generation."""
        code = "x = obj.member;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, PrimaryMember)
        assert isinstance(assignment.expr.left, Identifier)
        assert isinstance(assignment.expr.member, Identifier)
        assert assignment.expr.member.name == "member"


class TestPrimaryCallArguments:
    """arguments is always list[Argument] for PrimaryCall."""

    def test_zero_args(self):
        node = _getast("x = f();").expr
        assert isinstance(node, PrimaryCall)
        assert node.arguments == []
        assert isinstance(node.arguments, list)

    def test_one_positional(self):
        node = _getast("x = f(1);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 1
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_two_positional(self):
        node = _getast("x = f(1, 2);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 2
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_three_positional(self):
        node = _getast("x = f(1, 2, 3);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 3
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_one_named(self):
        node = _getast("x = f(a=1);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 1
        assert isinstance(node.arguments[0], NamedArgument)

    def test_two_named(self):
        node = _getast("x = f(a=1, b=2);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 2
        assert all(isinstance(a, NamedArgument) for a in node.arguments)

    def test_mixed(self):
        node = _getast("x = f(1, b=2);").expr
        assert isinstance(node, PrimaryCall)
        assert len(node.arguments) == 2
        assert isinstance(node.arguments[0], PositionalArgument)
        assert isinstance(node.arguments[1], NamedArgument)


class TestListComprehensionElements:
    """elements is always list[VectorElement] for ListComprehension."""

    def test_zero_elements(self):
        node = _getast("x = [];").expr
        assert isinstance(node, ListComprehension)
        assert node.elements == []
        assert isinstance(node.elements, list)

    def test_one_element(self):
        node = _getast("x = [1];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 1

    def test_two_elements(self):
        node = _getast("x = [1, 2];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 2

    def test_three_elements(self):
        node = _getast("x = [1, 2, 3];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 3

    def test_one_for_element(self):
        node = _getast("x = [for (i = [0:3]) i];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 1
        assert isinstance(node.elements[0], ListCompFor)

    def test_two_for_elements(self):
        node = _getast("x = [for (i = [0:3]) i, for (j = [0:2]) j];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 2
        assert all(isinstance(e, ListCompFor) for e in node.elements)

    def test_mixed_elements(self):
        node = _getast("x = [1, for (i = [0:2]) i, 3];").expr
        assert isinstance(node, ListComprehension)
        assert len(node.elements) == 3


class TestControlStructureASTNodes:
    """Test AST generation for control structures."""

    def test_let_expr_ast(self, parser):
        """Test LetOp AST node generation."""
        code = "x = let(a=1, b=2) a + b;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, LetOp)
        assert len(assignment.expr.assignments) == 2
        assert isinstance(assignment.expr.assignments[0], Assignment)
        assert isinstance(assignment.expr.body, AdditionOp)

    def test_echo_expr_ast(self, parser):
        """Test EchoOp AST node generation."""
        code = "x = echo(msg=\"test\") 5;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, EchoOp)
        assert len(assignment.expr.arguments) >= 1
        assert isinstance(assignment.expr.body, NumberLiteral)

    def test_assert_expr_ast(self, parser):
        """Test AssertOp AST node generation."""
        code = "x = assert(condition=true) 5;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, AssertOp)
        assert len(assignment.expr.arguments) >= 1
        assert isinstance(assignment.expr.body, NumberLiteral)


class TestModularCallArguments:
    """arguments is always list[Argument] for ModularCall."""

    def test_zero_args(self):
        node = _getast("cube();")
        assert isinstance(node, ModularCall)
        assert node.arguments == []
        assert isinstance(node.arguments, list)

    def test_one_positional(self):
        node = _getast("cube(10);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 1
        assert isinstance(node.arguments[0], PositionalArgument)

    def test_two_positional(self):
        node = _getast("foo(1, 2);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 2
        assert all(isinstance(a, PositionalArgument) for a in node.arguments)

    def test_three_positional(self):
        node = _getast("foo(1, 2, 3);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 3
        assert all(isinstance(a, PositionalArgument) for a in node.arguments)

    def test_one_named(self):
        node = _getast("translate(v=[1,0,0]);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 1
        assert isinstance(node.arguments[0], NamedArgument)

    def test_two_named(self):
        node = _getast("cube(size=10, center=true);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 2
        assert all(isinstance(a, NamedArgument) for a in node.arguments)

    def test_mixed(self):
        node = _getast("foo(1, b=2);")
        assert isinstance(node, ModularCall)
        assert len(node.arguments) == 2
        assert isinstance(node.arguments[0], PositionalArgument)
        assert isinstance(node.arguments[1], NamedArgument)


class TestModuleASTNodes:
    """Test AST generation for modules."""

    def test_module_declaration_ast(self, parser):
        """Test ModuleDeclaration AST node generation."""
        code = "module test(x, y=2) { cube(10); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 2
        assert isinstance(module.parameters[0], ParameterDeclaration)
        assert isinstance(module.parameters[1], ParameterDeclaration)

    def test_module_declaration_no_parameters(self, parser):
        """Test ModuleDeclaration with no parameters."""
        code = "module test() { cube(10); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 0

    def test_module_declaration_one_parameter_no_default(self, parser):
        """Test ModuleDeclaration with one parameter without default value."""
        code = "module test(x) { cube(x); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 1
        assert isinstance(module.parameters[0], ParameterDeclaration)
        assert isinstance(module.parameters[0].name, Identifier)
        assert module.parameters[0].name.name == "x"
        assert module.parameters[0].default is None

    def test_module_declaration_one_parameter_with_default(self, parser):
        """Test ModuleDeclaration with one parameter with default value."""
        code = "module test(x=10) { cube(x); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 1
        assert isinstance(module.parameters[0], ParameterDeclaration)
        assert isinstance(module.parameters[0].name, Identifier)
        assert module.parameters[0].name.name == "x"
        assert isinstance(module.parameters[0].default, NumberLiteral)
        assert module.parameters[0].default.val == 10

    def test_module_declaration_multiple_parameters_no_defaults(self, parser):
        """Test ModuleDeclaration with multiple parameters without default values."""
        code = "module test(x, y, z) { cube([x, y, z]); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 3
        for i, param in enumerate(module.parameters):
            assert isinstance(param, ParameterDeclaration)
            assert isinstance(param.name, Identifier)
            assert param.name.name == ["x", "y", "z"][i]
            assert param.default is None

    def test_module_declaration_multiple_parameters_with_defaults(self, parser):
        """Test ModuleDeclaration with multiple parameters with default values."""
        code = "module test(x=1, y=2, z=3) { cube([x, y, z]); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 3
        for i, param in enumerate(module.parameters):
            assert isinstance(param, ParameterDeclaration)
            assert isinstance(param.name, Identifier)
            assert param.name.name == ["x", "y", "z"][i]
            assert isinstance(param.default, NumberLiteral)
            assert param.default.val == [1, 2, 3][i]

    def test_module_declaration_mixed_parameters(self, parser):
        """Test ModuleDeclaration with mixed parameters (some with defaults, some without)."""
        code = "module test(x, y=2, z) { cube([x, y, z]); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 3
        # First parameter: no default
        assert isinstance(module.parameters[0], ParameterDeclaration)
        assert module.parameters[0].name.name == "x"
        assert module.parameters[0].default is None
        # Second parameter: with default
        assert isinstance(module.parameters[1], ParameterDeclaration)
        assert module.parameters[1].name.name == "y"
        assert isinstance(module.parameters[1].default, NumberLiteral)
        assert module.parameters[1].default.val == 2
        # Third parameter: no default
        assert isinstance(module.parameters[2], ParameterDeclaration)
        assert module.parameters[2].name.name == "z"
        assert module.parameters[2].default is None

    def test_module_declaration_no_children(self, parser):
        """Test ModuleDeclaration with no children (empty body)."""
        code = "module test() {}"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 0
        assert len(module.children) == 0

    def test_module_declaration_one_child(self, parser):
        """Test ModuleDeclaration with one child module instantiation."""
        code = "module test() { cube(10); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 0
        assert len(module.children) == 1
        assert isinstance(module.children[0], ModularCall)
        assert isinstance(module.children[0].name, Identifier)
        assert module.children[0].name.name == "cube"

    def test_module_declaration_multiple_children(self, parser):
        """Test ModuleDeclaration with multiple child module instantiations."""
        code = "module test() { cube(10); sphere(5); translate([1, 2, 3]) cylinder(1, 2); }"
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert isinstance(module.name, Identifier)
        assert module.name.name == "test"
        assert len(module.parameters) == 0
        assert len(module.children) == 3
        
        # First child: cube
        assert isinstance(module.children[0], ModularCall)
        assert isinstance(module.children[0].name, Identifier)
        assert module.children[0].name.name == "cube"
        
        # Second child: sphere
        assert isinstance(module.children[1], ModularCall)
        assert isinstance(module.children[1].name, Identifier)
        assert module.children[1].name.name == "sphere"
        
        # Third child: translate with cylinder as child
        assert isinstance(module.children[2], ModularCall)
        assert isinstance(module.children[2].name, Identifier)
        assert module.children[2].name.name == "translate"
        assert len(module.children[2].children) == 1
        assert isinstance(module.children[2].children[0], ModularCall)
        assert isinstance(module.children[2].children[0].name, Identifier)
        assert module.children[2].children[0].name.name == "cylinder"

    def test_module_call_no_arguments(self, parser):
        """Test ModularCall with no arguments."""
        code = "cube();"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.arguments) == 0

    def test_module_call_one_positional_argument(self, parser):
        """Test ModularCall with one positional argument."""
        code = "cube(10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.arguments) == 1
        assert isinstance(call.arguments[0], PositionalArgument)
        assert isinstance(call.arguments[0].expr, NumberLiteral)
        assert call.arguments[0].expr.val == 10

    def test_module_call_multiple_positional_arguments(self, parser):
        """Test ModularCall with multiple positional arguments."""
        code = "translate([1, 2, 3]) cube(10);"
        ast = parse_ast(parser, code)
        # First statement should be translate
        translate_call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(translate_call, ModularCall)
        assert isinstance(translate_call.name, Identifier)
        assert translate_call.name.name == "translate"
        assert len(translate_call.arguments) == 1
        assert isinstance(translate_call.arguments[0], PositionalArgument)

    def test_module_call_ast(self, parser):
        """Test ModularCall AST node generation."""
        code = "cube(10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.arguments) == 1

    def test_module_call_named_arguments(self, parser):
        """Test ModularCall with named arguments."""
        code = "cube(size=10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.arguments) == 1
        assert isinstance(call.arguments[0], NamedArgument)
        assert isinstance(call.arguments[0].name, Identifier)
        assert call.arguments[0].name.name == "size"
        assert isinstance(call.arguments[0].expr, NumberLiteral)
        assert call.arguments[0].expr.val == 10

    def test_module_call_multiple_named_arguments(self, parser):
        """Test ModularCall with multiple named arguments."""
        code = "cube(size=[10, 20, 30], center=true);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.arguments) == 2
        assert isinstance(call.arguments[0], NamedArgument)
        assert isinstance(call.arguments[0].name, Identifier)
        assert call.arguments[0].name.name == "size"
        assert isinstance(call.arguments[1], NamedArgument)
        assert isinstance(call.arguments[1].name, Identifier)
        assert call.arguments[1].name.name == "center"

    def test_module_call_mixed_arguments(self, parser):
        """Test ModularCall with mixed positional and named arguments."""
        code = "foo(1, b=2);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "foo"
        assert len(call.arguments) == 2
        assert isinstance(call.arguments[0], PositionalArgument)
        assert isinstance(call.arguments[1], NamedArgument)
        assert isinstance(call.arguments[1].name, Identifier)
        assert call.arguments[1].name.name == "b"

    def test_module_call_no_children(self, parser):
        """Test ModularCall with no children."""
        code = "cube(10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "cube"
        assert len(call.children) == 0

    def test_module_call_one_child(self, parser):
        """Test ModularCall with one child module instantiation."""
        code = "translate([1, 2, 3]) cube(10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "translate"
        assert len(call.children) == 1
        assert isinstance(call.children[0], ModularCall)
        assert isinstance(call.children[0].name, Identifier)
        assert call.children[0].name.name == "cube"

    def test_module_call_multiple_children_chained(self, parser):
        """Test ModularCall with multiple children via chained calls."""
        code = "translate([1, 2, 3]) rotate([0, 0, 45]) cube(10);"
        ast = parse_ast(parser, code)
        call = ast[0] if isinstance(ast, list) else ast
        assert isinstance(call, ModularCall)
        assert isinstance(call.name, Identifier)
        assert call.name.name == "translate"
        assert len(call.children) == 1
        
        # First child: rotate
        assert isinstance(call.children[0], ModularCall)
        assert isinstance(call.children[0].name, Identifier)
        assert call.children[0].name.name == "rotate"
        assert len(call.children[0].children) == 1
        
        # Second child (nested): cube
        assert isinstance(call.children[0].children[0], ModularCall)
        assert isinstance(call.children[0].children[0].name, Identifier)
        assert call.children[0].children[0].name.name == "cube"

    def test_modular_for_ast(self, parser):
        """Test ModularFor AST node generation."""
        code = "for (i=[0:2]) cube(i);"
        ast = parse_ast(parser, code)
        for_stmt = ast[0] if isinstance(ast, list) else ast
        assert isinstance(for_stmt, ModularFor)
        assert len(for_stmt.assignments) == 1
        assert isinstance(for_stmt.body, list)
        assert len(for_stmt.body) == 1
        assert isinstance(for_stmt.body[0], ModularCall)

    def test_modular_if_ast(self, parser):

        """Test ModularIf AST node generation."""
        code = "if (true) cube(10);"
        ast = parse_ast(parser, code)
        if_stmt = ast[0] if isinstance(ast, list) else ast
        assert isinstance(if_stmt, ModularIf)
        assert isinstance(if_stmt.condition, BooleanLiteral)
        assert isinstance(if_stmt.true_branch, list)
        assert len(if_stmt.true_branch) == 1
        assert isinstance(if_stmt.true_branch[0], ModularCall)

    def test_modular_if_else_ast(self, parser):
        """Test ModularIfElse AST node generation."""
        code = "if (true) cube(10); else sphere(5);"
        ast = parse_ast(parser, code)
        if_stmt = ast[0] if isinstance(ast, list) else ast
        assert isinstance(if_stmt, ModularIfElse)
        assert isinstance(if_stmt.condition, BooleanLiteral)
        assert isinstance(if_stmt.true_branch, list)
        assert isinstance(if_stmt.false_branch, list)
        assert isinstance(if_stmt.true_branch[0], ModularCall)
        assert isinstance(if_stmt.false_branch[0], ModularCall)

    def test_modifier_show_only_ast(self, parser):
        """Test ModularModifierShowOnly AST node generation."""
        code = "!cube(10);"
        ast = parse_ast(parser, code)
        modifier = ast[0] if isinstance(ast, list) else ast
        assert isinstance(modifier, ModularModifierShowOnly)
        assert isinstance(modifier.child, ModularCall)

    def test_modifier_highlight_ast(self, parser):
        """Test ModularModifierHighlight AST node generation."""
        code = "#cube(10);"
        ast = parse_ast(parser, code)
        modifier = ast[0] if isinstance(ast, list) else ast
        assert isinstance(modifier, ModularModifierHighlight)

    def test_modifier_background_ast(self, parser):
        """Test ModularModifierBackground AST node generation."""
        code = "%cube(10);"
        ast = parse_ast(parser, code)
        modifier = ast[0] if isinstance(ast, list) else ast
        assert isinstance(modifier, ModularModifierBackground)

    def test_modifier_disable_ast(self, parser):
        """Test ModularModifierDisable AST node generation."""
        code = "*cube(10);"
        ast = parse_ast(parser, code)
        modifier = ast[0] if isinstance(ast, list) else ast
        assert isinstance(modifier, ModularModifierDisable)


def _getast(code):
    ast = getASTfromString(code)
    return ast[0]


class TestLetAssignments:
    """assignments is always list[Assignment] for let/for nodes."""

    # --- LetOp (expression-level let) ---

    def test_let_op_zero(self):
        node = _getast("x = let() 5;").expr
        assert isinstance(node, LetOp)
        assert node.assignments == []
        assert isinstance(node.assignments, list)

    def test_let_op_one(self):
        node = _getast("x = let(a=1) a;").expr
        assert isinstance(node, LetOp)
        assert len(node.assignments) == 1
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_let_op_two(self):
        node = _getast("x = let(a=1, b=2) a+b;").expr
        assert isinstance(node, LetOp)
        assert len(node.assignments) == 2
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_let_op_three(self):
        node = _getast("x = let(a=1, b=2, c=3) a+b+c;").expr
        assert isinstance(node, LetOp)
        assert len(node.assignments) == 3
        assert all(isinstance(a, Assignment) for a in node.assignments)

    # --- ModularLet (statement-level let) ---

    def test_modular_let_zero(self):
        node = _getast("let() cube(1);")
        assert isinstance(node, ModularLet)
        assert node.assignments == []
        assert isinstance(node.assignments, list)

    def test_modular_let_one(self):
        node = _getast("let(x=1) cube(x);")
        assert isinstance(node, ModularLet)
        assert len(node.assignments) == 1
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_let_two(self):
        node = _getast("let(x=1, y=2) cube(x);")
        assert isinstance(node, ModularLet)
        assert len(node.assignments) == 2
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_let_three(self):
        node = _getast("let(x=1, y=2, z=3) cube(x);")
        assert isinstance(node, ModularLet)
        assert len(node.assignments) == 3
        assert all(isinstance(a, Assignment) for a in node.assignments)

    # --- ModularFor ---

    def test_modular_for_one(self):
        node = _getast("for (i=[0:3]) cube(i);")
        assert isinstance(node, ModularFor)
        assert len(node.assignments) == 1
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_for_two(self):
        node = _getast("for (i=[0:3], j=[0:2]) cube(i);")
        assert isinstance(node, ModularFor)
        assert len(node.assignments) == 2
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_for_three(self):
        node = _getast("for (i=[0:3], j=[0:2], k=[0:1]) cube(i);")
        assert isinstance(node, ModularFor)
        assert len(node.assignments) == 3
        assert all(isinstance(a, Assignment) for a in node.assignments)

    # --- ModularIntersectionFor ---

    def test_modular_intersection_for_one(self):
        node = _getast("intersection_for (i=[0:3]) cube(i);")
        assert isinstance(node, ModularIntersectionFor)
        assert len(node.assignments) == 1
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_intersection_for_two(self):
        node = _getast("intersection_for (i=[0:3], j=[0:2]) cube(i);")
        assert isinstance(node, ModularIntersectionFor)
        assert len(node.assignments) == 2
        assert all(isinstance(a, Assignment) for a in node.assignments)

    def test_modular_intersection_for_three(self):
        node = _getast("intersection_for (i=[0:3], j=[0:2], k=[0:1]) cube(i);")
        assert isinstance(node, ModularIntersectionFor)
        assert len(node.assignments) == 3
        assert all(isinstance(a, Assignment) for a in node.assignments)


class TestModuleDeclarationChildren:
    """children is always list for ModuleDeclaration."""

    def test_zero_children(self):
        node = _getast("module foo() {}")
        assert isinstance(node, ModuleDeclaration)
        assert node.children == []
        assert isinstance(node.children, list)

    def test_one_child(self):
        node = _getast("module foo() { cube(1); }")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.children) == 1
        assert isinstance(node.children[0], ModularCall)

    def test_two_children(self):
        node = _getast("module foo() { cube(1); sphere(1); }")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.children) == 2
        assert all(isinstance(c, ModularCall) for c in node.children)

    def test_three_children(self):
        node = _getast("module foo() { cube(1); sphere(1); cylinder(1); }")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.children) == 3
        assert all(isinstance(c, ModularCall) for c in node.children)

    def test_empty_statement_body(self):
        node = _getast("module foo() ;")
        assert isinstance(node, ModuleDeclaration)
        assert node.children == []

    def test_single_statement_body(self):
        node = _getast("module foo() cube(10);")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.children) == 1
        assert isinstance(node.children[0], ModularCall)


class TestFunctionASTNodes:
    """Test AST generation for functions."""

    def test_function_declaration_ast(self, parser):
        """Test FunctionDeclaration AST node generation."""
        code = "function test(x, y=2) = x + y;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 2
        assert isinstance(func.expr, AdditionOp)

    def test_function_declaration_no_parameters(self, parser):
        """Test FunctionDeclaration with no parameters."""
        code = "function test() = 5;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 0
        assert isinstance(func.expr, NumberLiteral)
        assert func.expr.val == 5

    def test_function_declaration_one_parameter_no_default(self, parser):
        """Test FunctionDeclaration with one parameter without default value."""
        code = "function test(x) = x;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 1
        assert isinstance(func.parameters[0], ParameterDeclaration)
        assert isinstance(func.parameters[0].name, Identifier)
        assert func.parameters[0].name.name == "x"
        assert func.parameters[0].default is None
        assert isinstance(func.expr, Identifier)
        assert func.expr.name == "x"

    def test_function_declaration_one_parameter_with_default(self, parser):
        """Test FunctionDeclaration with one parameter with default value."""
        code = "function test(x=10) = x;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 1
        assert isinstance(func.parameters[0], ParameterDeclaration)
        assert isinstance(func.parameters[0].name, Identifier)
        assert func.parameters[0].name.name == "x"
        assert isinstance(func.parameters[0].default, NumberLiteral)
        assert func.parameters[0].default.val == 10
        assert isinstance(func.expr, Identifier)
        assert func.expr.name == "x"

    def test_function_declaration_multiple_parameters_no_defaults(self, parser):
        """Test FunctionDeclaration with multiple parameters without default values."""
        code = "function test(x, y) = x + y;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 2
        for i, param in enumerate(func.parameters):
            assert isinstance(param, ParameterDeclaration)
            assert isinstance(param.name, Identifier)
            assert param.name.name == ["x", "y"][i]
            assert param.default is None
        assert isinstance(func.expr, AdditionOp)

    def test_function_declaration_multiple_parameters_with_defaults(self, parser):
        """Test FunctionDeclaration with multiple parameters with default values."""
        code = "function test(x=1, y=2) = x + y;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 2
        for i, param in enumerate(func.parameters):
            assert isinstance(param, ParameterDeclaration)
            assert isinstance(param.name, Identifier)
            assert param.name.name == ["x", "y"][i]
            assert isinstance(param.default, NumberLiteral)
            assert param.default.val == [1, 2][i]
        assert isinstance(func.expr, AdditionOp)

    def test_function_declaration_mixed_parameters(self, parser):
        """Test FunctionDeclaration with mixed parameters (some with defaults, some without)."""
        code = "function test(x, y=2, z) = x + y + z;"
        ast = parse_ast(parser, code)
        func = ast[0] if isinstance(ast, list) else ast
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(func.name, Identifier)
        assert func.name.name == "test"
        assert len(func.parameters) == 3
        # First parameter: no default
        assert isinstance(func.parameters[0], ParameterDeclaration)
        assert func.parameters[0].name.name == "x"
        assert func.parameters[0].default is None
        # Second parameter: with default
        assert isinstance(func.parameters[1], ParameterDeclaration)
        assert func.parameters[1].name.name == "y"
        assert isinstance(func.parameters[1].default, NumberLiteral)
        assert func.parameters[1].default.val == 2
        # Third parameter: no default
        assert isinstance(func.parameters[2], ParameterDeclaration)
        assert func.parameters[2].name.name == "z"
        assert func.parameters[2].default is None
        assert isinstance(func.expr, AdditionOp)

    def test_function_literal_ast(self, parser):
        """Test FunctionLiteral AST node generation."""
        code = "x = function(x) x * 2;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, FunctionLiteral)
        assert isinstance(assignment.expr.body, MultiplicationOp)


class TestDeclarationParameters:
    """parameters is always list[ParameterDeclaration] for module/function declarations."""

    # --- ModuleDeclaration ---

    def test_module_zero_params(self):
        node = _getast("module foo() {}")
        assert isinstance(node, ModuleDeclaration)
        assert node.parameters == []
        assert isinstance(node.parameters, list)

    def test_module_one_param(self):
        node = _getast("module foo(a) {}")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.parameters) == 1
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_module_two_params(self):
        node = _getast("module foo(a, b) {}")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.parameters) == 2
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_module_three_params(self):
        node = _getast("module foo(a, b, c) {}")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_module_params_with_defaults(self):
        node = _getast("module foo(a, b=2, c=3) {}")
        assert isinstance(node, ModuleDeclaration)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    # --- FunctionDeclaration ---

    def test_function_zero_params(self):
        node = _getast("function f() = 1;")
        assert isinstance(node, FunctionDeclaration)
        assert node.parameters == []
        assert isinstance(node.parameters, list)

    def test_function_one_param(self):
        node = _getast("function f(x) = x;")
        assert isinstance(node, FunctionDeclaration)
        assert len(node.parameters) == 1
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_two_params(self):
        node = _getast("function f(x, y) = x + y;")
        assert isinstance(node, FunctionDeclaration)
        assert len(node.parameters) == 2
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_three_params(self):
        node = _getast("function f(x, y, z) = x + y + z;")
        assert isinstance(node, FunctionDeclaration)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_params_with_defaults(self):
        node = _getast("function f(x, y=2, z=3) = x + y + z;")
        assert isinstance(node, FunctionDeclaration)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    # --- FunctionLiteral ---

    def test_function_literal_zero_params(self):
        node = _getast("x = function() 1;").expr
        assert isinstance(node, FunctionLiteral)
        assert node.parameters == []
        assert isinstance(node.parameters, list)

    def test_function_literal_one_param(self):
        node = _getast("x = function(a) a;").expr
        assert isinstance(node, FunctionLiteral)
        assert len(node.parameters) == 1
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_literal_two_params(self):
        node = _getast("x = function(a, b) a + b;").expr
        assert isinstance(node, FunctionLiteral)
        assert len(node.parameters) == 2
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_literal_three_params(self):
        node = _getast("x = function(a, b, c) a + b + c;").expr
        assert isinstance(node, FunctionLiteral)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)

    def test_function_literal_params_with_defaults(self):
        node = _getast("x = function(a, b=2, c=3) a + b + c;").expr
        assert isinstance(node, FunctionLiteral)
        assert len(node.parameters) == 3
        assert all(isinstance(p, ParameterDeclaration) for p in node.parameters)


class TestEchoArguments:
    """arguments is always list[Argument] for echo/assert nodes."""

    # --- EchoOp (expression form) ---

    def test_echo_op_zero(self):
        node = _getast("x = echo() 5;").expr
        assert isinstance(node, EchoOp)
        assert node.arguments == []
        assert isinstance(node.arguments, list)

    def test_echo_op_one(self):
        node = _getast("x = echo(1) 5;").expr
        assert isinstance(node, EchoOp)
        assert len(node.arguments) == 1
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_echo_op_two(self):
        node = _getast("x = echo(1, 2) 5;").expr
        assert isinstance(node, EchoOp)
        assert len(node.arguments) == 2
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_echo_op_three(self):
        node = _getast("x = echo(1, 2, 3) 5;").expr
        assert isinstance(node, EchoOp)
        assert len(node.arguments) == 3
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    # --- ModularEcho (statement form) ---

    def test_modular_echo_zero(self):
        node = _getast("echo();")
        assert isinstance(node, ModularEcho)
        assert node.arguments == []
        assert isinstance(node.arguments, list)

    def test_modular_echo_one(self):
        node = _getast("echo(1);")
        assert isinstance(node, ModularEcho)
        assert len(node.arguments) == 1
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_modular_echo_two(self):
        node = _getast("echo(1, 2);")
        assert isinstance(node, ModularEcho)
        assert len(node.arguments) == 2
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_modular_echo_three(self):
        node = _getast("echo(1, 2, 3);")
        assert isinstance(node, ModularEcho)
        assert len(node.arguments) == 3
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    # --- ModularAssert (statement form) ---

    def test_modular_assert_one(self):
        node = _getast("assert(true);")
        assert isinstance(node, ModularAssert)
        assert len(node.arguments) == 1
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_modular_assert_two(self):
        node = _getast("assert(true, \"msg\");")
        assert isinstance(node, ModularAssert)
        assert len(node.arguments) == 2
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)

    def test_modular_assert_three(self):
        node = _getast("assert(true, \"a\", \"b\");")
        assert isinstance(node, ModularAssert)
        assert len(node.arguments) == 3
        assert all(isinstance(a, (PositionalArgument, NamedArgument)) for a in node.arguments)


class TestStatementASTNodes:
    """Test AST generation for statements."""

    def test_use_statement_ast(self, parser):
        """Test UseStatement AST node generation."""
        code = "use <test.scad>"
        ast = parse_ast(parser, code)
        use_stmt = ast[0] if isinstance(ast, list) else ast
        assert isinstance(use_stmt, UseStatement)
        assert isinstance(use_stmt.filepath, StringLiteral)
        assert use_stmt.filepath.val == "test.scad"

    def test_include_statement_ast(self, parser):
        """Test IncludeStatement AST node generation."""
        code = "include <test.scad>"
        ast = parse_ast(parser, code)
        include_stmt = ast[0] if isinstance(ast, list) else ast
        assert isinstance(include_stmt, IncludeStatement)
        assert isinstance(include_stmt.filepath, StringLiteral)
        assert include_stmt.filepath.val == "test.scad"

    def test_assignment_ast(self, parser):
        """Test Assignment AST node generation."""
        code = "x = 5;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert isinstance(assignment, Assignment)
        assert isinstance(assignment.name, Identifier)
        assert assignment.name.name == "x"
        assert isinstance(assignment.expr, NumberLiteral)
        assert assignment.expr.val == 5.0


class TestPositionASTNodes:
    """Test AST node position information."""

    def test_position_information(self, parser):
        """Test that AST nodes have position information."""
        code = "x = 5;"
        ast = parse_ast(parser, code, file="test.scad")
        assignment = ast[0] if isinstance(ast, list) else ast
        assert hasattr(assignment, 'position')
        assert assignment is not None
        assert isinstance(assignment.position, Position)
        assert assignment.position.origin == "test.scad"
        # Test line and column
        assert assignment.position.line >= 1
        assert assignment.position.column >= 1

    def test_position_lazy_evaluation(self, parser):
        """Test that position line/char are calculated lazily."""
        code = "x = 5;\ny = 10;"
        ast = parse_ast(parser, code, file="test.scad")
        assert ast is not None
        assert len(ast) >= 2
        # Second assignment should be on line 2
        assert ast[1].position.line == 2


class TestComplexASTNodes:
    """Test AST generation for complex constructs."""

    def test_nested_expressions_ast(self, parser):
        """Test nested expression AST structure."""
        code = "x = (1 + 2) * 3;"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        assert assignment.expr is not None
        assert isinstance(assignment.expr, MultiplicationOp)
        assert isinstance(assignment.expr.left, AdditionOp)

    def test_chained_function_calls_ast(self, parser):
        """Test chained function call AST structure."""
        code = "x = foo(1)(2);"
        ast = parse_ast(parser, code)
        assignment = ast[0] if isinstance(ast, list) else ast
        assert assignment is not None
        assert isinstance(assignment, Assignment)
        # Should be: PrimaryCall(PrimaryCall(Identifier("foo"), [1]), [2])
        assert isinstance(assignment.expr, PrimaryCall)
        assert isinstance(assignment.expr.left, PrimaryCall)

    def test_complex_module_ast(self, parser):
        """Test complex module with multiple statements."""
        code = """
        module test(x, y=2) {
            a = x + y;
            cube(a);
            sphere(a/2);
        }
        """
        ast = parse_ast(parser, code)
        module = ast[0] if isinstance(ast, list) else ast
        assert isinstance(module, ModuleDeclaration)
        assert len(module.children) >= 2  # Should have cube and sphere calls


def _expr(parser, code: str):
    """Parse ``x = <code>;`` and return the RHS expression node."""
    ast = parse_ast(parser, f"x = {code};")
    assert ast is not None and len(ast) == 1
    node = ast[0]
    assert isinstance(node, Assignment)
    return node.expr


class TestLogicalNotAST:
    """AST-level tests for the logical NOT operator (!)."""

    def test_not_true(self, parser):
        """! applied to boolean literal true."""
        expr = _expr(parser, "!true")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, BooleanLiteral)
        assert expr.expr.val is True

    def test_not_false(self, parser):
        """! applied to boolean literal false."""
        expr = _expr(parser, "!false")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, BooleanLiteral)
        assert expr.expr.val is False

    def test_not_identifier(self, parser):
        """! applied to a variable."""
        expr = _expr(parser, "!a")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, Identifier)
        assert expr.expr.name == "a"

    def test_not_double(self, parser):
        """!! is LogicalNotOp wrapping LogicalNotOp."""
        expr = _expr(parser, "!!a")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, LogicalNotOp)
        assert isinstance(expr.expr.expr, Identifier)

    def test_not_equality(self, parser):
        """! applied to a parenthesized equality expression."""
        expr = _expr(parser, "!(a == b)")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, EqualityOp)

    def test_not_inequality(self, parser):
        """! applied to a parenthesized inequality expression."""
        expr = _expr(parser, "!(a != b)")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, InequalityOp)

    def test_not_comparison(self, parser):
        """! applied to a parenthesized greater-than comparison."""
        expr = _expr(parser, "!(a > 0)")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, GreaterThanOp)

    def test_not_binds_tighter_than_logical_and(self, parser):
        """!a && b is ((!a) && b), not !(a && b)."""
        expr = _expr(parser, "!a && b")
        assert isinstance(expr, LogicalAndOp)
        assert isinstance(expr.left, LogicalNotOp)
        assert expr.left.expr.name == "a"
        assert isinstance(expr.right, Identifier)
        assert expr.right.name == "b"

    def test_not_both_sides_of_and(self, parser):
        """!a && !b — both AND operands are negated."""
        expr = _expr(parser, "!a && !b")
        assert isinstance(expr, LogicalAndOp)
        assert isinstance(expr.left, LogicalNotOp)
        assert isinstance(expr.right, LogicalNotOp)

    def test_not_binds_tighter_than_logical_or(self, parser):
        """!a || b is ((!a) || b)."""
        expr = _expr(parser, "!a || b")
        assert isinstance(expr, LogicalOrOp)
        assert isinstance(expr.left, LogicalNotOp)
        assert isinstance(expr.right, Identifier)

    def test_not_in_ternary_condition(self, parser):
        """!a used as ternary condition."""
        expr = _expr(parser, "!a ? 1 : 2")
        assert isinstance(expr, TernaryOp)
        assert isinstance(expr.condition, LogicalNotOp)

    def test_not_in_ternary_branch(self, parser):
        """!b in the true branch of a ternary."""
        expr = _expr(parser, "a ? !b : c")
        assert isinstance(expr, TernaryOp)
        assert isinstance(expr.true_expr, LogicalNotOp)

    def test_not_in_if_condition(self, parser):
        """! used as a condition in an if statement."""
        ast = parse_ast(parser, "if (!cond) cube();")
        assert ast is not None and len(ast) == 1
        node = ast[0]
        assert isinstance(node, ModularIf)
        assert isinstance(node.condition, LogicalNotOp)
        assert isinstance(node.condition.expr, Identifier)
        assert node.condition.expr.name == "cond"

    def test_str_simple(self, parser):
        """__str__ renders !true as !true."""
        expr = _expr(parser, "!true")
        assert str(expr) == "!true"

    def test_str_double(self, parser):
        """__str__ renders !!a as !!a."""
        expr = _expr(parser, "!!a")
        assert str(expr) == "!!a"


class TestBitwiseNotAST:
    """AST-level tests for the bitwise NOT operator (~)."""

    def test_not_number(self, parser):
        """~ applied to a number literal."""
        expr = _expr(parser, "~5")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, NumberLiteral)
        assert expr.expr.val == 5

    def test_not_identifier(self, parser):
        """~ applied to a variable."""
        expr = _expr(parser, "~a")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, Identifier)
        assert expr.expr.name == "a"

    def test_not_double(self, parser):
        """~~ is BitwiseNotOp wrapping BitwiseNotOp."""
        expr = _expr(parser, "~~a")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, BitwiseNotOp)
        assert isinstance(expr.expr.expr, Identifier)

    def test_not_parenthesized_addition(self, parser):
        """~ applied to a parenthesized addition."""
        expr = _expr(parser, "~(a + b)")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, AdditionOp)

    def test_not_parenthesized_shift(self, parser):
        """~ applied to a parenthesized left-shift expression."""
        expr = _expr(parser, "~(a << b)")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, BitwiseShiftLeftOp)

    def test_not_binds_tighter_than_bitwise_and(self, parser):
        """~a & b is ((~a) & b), not ~(a & b)."""
        expr = _expr(parser, "~a & b")
        assert isinstance(expr, BitwiseAndOp)
        assert isinstance(expr.left, BitwiseNotOp)
        assert expr.left.expr.name == "a"
        assert isinstance(expr.right, Identifier)
        assert expr.right.name == "b"

    def test_not_both_sides_of_and(self, parser):
        """~a & ~b — both AND operands are complemented."""
        expr = _expr(parser, "~a & ~b")
        assert isinstance(expr, BitwiseAndOp)
        assert isinstance(expr.left, BitwiseNotOp)
        assert isinstance(expr.right, BitwiseNotOp)

    def test_not_binds_tighter_than_bitwise_or(self, parser):
        """~a | b is ((~a) | b)."""
        expr = _expr(parser, "~a | b")
        assert isinstance(expr, BitwiseOrOp)
        assert isinstance(expr.left, BitwiseNotOp)
        assert isinstance(expr.right, Identifier)

    def test_str_simple(self, parser):
        """__str__ renders ~5 as ~5 (whole-number floats omit the .0 suffix)."""
        expr = _expr(parser, "~5")
        assert str(expr) == "~5"

    def test_str_double(self, parser):
        """__str__ renders ~~a as ~~a."""
        expr = _expr(parser, "~~a")
        assert str(expr) == "~~a"


class TestMixedNotOperatorsAST:
    """AST-level tests for combinations of ! and ~ in the same expression."""

    def test_bitwise_not_of_logical_not(self, parser):
        """~!a — BitwiseNotOp wrapping LogicalNotOp."""
        expr = _expr(parser, "~!a")
        assert isinstance(expr, BitwiseNotOp)
        assert isinstance(expr.expr, LogicalNotOp)
        assert isinstance(expr.expr.expr, Identifier)

    def test_logical_not_of_bitwise_not(self, parser):
        """!~a — LogicalNotOp wrapping BitwiseNotOp."""
        expr = _expr(parser, "!~a")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, BitwiseNotOp)
        assert isinstance(expr.expr.expr, Identifier)

    def test_three_levels_of_nesting(self, parser):
        """!~!a — three alternating levels of not operators."""
        expr = _expr(parser, "!~!a")
        assert isinstance(expr, LogicalNotOp)
        assert isinstance(expr.expr, BitwiseNotOp)
        assert isinstance(expr.expr.expr, LogicalNotOp)
        assert isinstance(expr.expr.expr.expr, Identifier)

