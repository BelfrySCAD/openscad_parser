"""Tests for ASTBuilderVisitor edge cases and error handling."""

import pytest
from openscad_parser import getOpenSCADParser
from openscad_parser.ast.builder import ASTBuilderVisitor, Position, SemanticChildren
from openscad_parser.ast.source_map import SourceMap
from openscad_parser.ast.nodes import (
    Identifier, StringLiteral, NumberLiteral, BooleanLiteral, UndefinedLiteral,
    ModuleDeclaration, FunctionDeclaration, UseStatement, IncludeStatement,
    Assignment, LetOp, AssertOp, EchoOp, TernaryOp, Expression,
    PrimaryCall, ModularCall, ModularFor, ModularCFor, ModularLet, ModularEcho,
    ModularAssert, ModularIntersectionFor, ModularIntersectionCFor,
    ListComprehension, BitwiseNotOp, LogicalNotOp, CommentLine, CommentSpan,
    MultiplicationOp, UnaryMinusOp, PositionalArgument
)
from arpeggio import NonTerminal, Terminal, NoMatch


class TestPosition:
    """Test Position class edge cases."""

    def test_position_edge_cases(self):
        """Test Position with edge cases."""
        # Test with basic position
        pos = Position(origin="test.scad", line=1, column=1)
        assert pos.line == 1
        assert pos.column == 1
        assert pos.origin == "test.scad"
        
        # Test with different values
        pos = Position(origin="test.scad", line=2, column=5)
        assert pos.line == 2
        assert pos.column == 5
        
        # Test with unknown origin
        pos = Position(origin="<unknown>", line=1, column=1)
        assert pos.origin == "<unknown>"

    def test_position_repr(self):
        """Test Position __repr__ output."""
        pos = Position(origin="file.scad", line=3, column=7)
        assert repr(pos) == "file.scad:3:7"


class TestASTBuilderVisitorEdgeCases:
    """Test ASTBuilderVisitor edge cases and error handling."""

    def test_visit_node_with_none(self):
        """Test _visit_node with None."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        result = visitor._visit_node(None)
        assert result is None

    def test_visit_node_terminal_without_value(self):
        """Test _visit_node with terminal node without value attribute."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        # Create a mock terminal node
        class MockTerminal:
            pass
        terminal = MockTerminal()
        result = visitor._visit_node(terminal)
        assert result == terminal

    def test_visit_node_exception_handling(self):
        """Test _visit_node exception handling in visit method."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        # Create a mock node that will cause an exception
        class MockNode:
            rule_name = "test_rule"
            def __iter__(self):
                return iter([])
        
        # Add a visit method that raises an exception
        def visit_test_rule(node, children):
            raise ValueError("Test exception")
        
        visitor.visit_test_rule = visit_test_rule  # type: ignore
        
        node = MockNode()
        result = visitor._visit_node(node)
        # Should return None when exception occurs and no children
        assert result is None

    def test_visit_node_exception_with_children(self):
        """Test _visit_node exception handling with children."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockChild:
            pass
        
        class MockNode:
            rule_name = "test_rule"
            def __iter__(self):
                return iter([MockChild()])
        
        def visit_test_rule(node, children):
            raise ValueError("Test exception")
        
        visitor.visit_test_rule = visit_test_rule  # type: ignore
        
        node = MockNode()
        result = visitor._visit_node(node)
        # Should return children when exception occurs
        assert result is not None

    def test_semantic_children_rule_access(self):
        """Test SemanticChildren rule-based access."""
        items = ["a", "b"]
        rule_map = {"rule_a": ["x"], "rule_b": ["y", "z"]}
        children = SemanticChildren(items, rule_map)
        assert children.rule_a == ["x"]
        assert children.rule_b == ["y", "z"]
        assert children.unknown_rule == []

    def test_visit_parse_tree_delegates(self):
        """Test visit_parse_tree delegates to _visit_node."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            rule_name = "test_rule"
            def __iter__(self):
                return iter([])

        def visit_test_rule(node, children):
            return "ok"

        visitor.visit_test_rule = visit_test_rule  # type: ignore
        result = visitor.visit_parse_tree(MockNode())
        assert result == "ok"

    def test_get_node_position_without_position(self):
        """Test _get_node_position with node without position attribute."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            pass
        
        node = MockNode()
        pos = visitor._get_node_position(node)
        assert pos.line >= 1
        assert pos.column >= 1

    def test_get_node_position_with_source_map(self):
        """Test _get_node_position with source_map."""
        parser = getOpenSCADParser()
        source_map = SourceMap()
        source_map.add_origin("test.scad", "x = 5;")
        visitor = ASTBuilderVisitor(parser, source_map=source_map)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        pos = visitor._get_node_position(node)
        assert pos.origin == "test.scad"

    def test_visit_module_definition_missing_name(self):
        """Test visit_module_definition with missing name."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="module_definition should have a name"):
            visitor.visit_module_definition(node, [])

    def test_visit_module_definition_with_list_parameters(self):
        """Test visit_module_definition with list of parameters."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import ParameterDeclaration
        
        name = Identifier(name="test", position=Position("", 1, 1))
        param1 = ParameterDeclaration(name=Identifier(name="x", position=Position("", 1, 1)), 
                                     default=None, position=Position("", 1, 1))
        param2 = ParameterDeclaration(name=Identifier(name="y", position=Position("", 1, 1)), 
                                     default=None, position=Position("", 1, 1))
        
        class MockNode:
            position = 0
        
        node = MockNode()
        # Test with list of parameters
        result = visitor.visit_module_definition(node, [name, [param1, param2], "body"])
        assert isinstance(result, ModuleDeclaration)
        assert len(result.parameters) == 2

    def test_visit_module_definition_with_nested_lists(self):
        """Test visit_module_definition with nested lists in body."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import ModularCall
        
        name = Identifier(name="test", position=Position("", 1, 1))
        # Create a proper ModuleInstantiation using ModularCall
        mod_inst = ModularCall(
            name=Identifier(name="cube", position=Position("", 1, 1)),
            arguments=[],
            children=[],
            position=Position("", 1, 1)
        )
        
        class MockNode:
            position = 0
        
        node = MockNode()
        # Test with nested lists
        result = visitor.visit_module_definition(node, [name, [], [[mod_inst]]])
        assert isinstance(result, ModuleDeclaration)

    def test_visit_function_definition_missing_name(self):
        """Test visit_function_definition with missing name."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="FunctionDeclarationNode should have an Identifier"):
            visitor.visit_function_definition(node, [])

    def test_visit_function_definition_missing_expression(self):
        """Test visit_function_definition with missing expression."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        name = Identifier(name="test", position=Position("", 1, 1))
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="FunctionDeclarationNode should have an Expression"):
            visitor.visit_function_definition(node, [name])

    def test_visit_use_statement_error_cases(self):
        """Test visit_use_statement error cases."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
            def __iter__(self):
                return iter([])  # Empty children
        
        node = MockNode()
        with pytest.raises(ValueError, match="UseStatementNode should have a filepath"):
            visitor.visit_use_statement(node, [])

    def test_visit_include_statement_error_cases(self):
        """Test visit_include_statement error cases."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
            def __iter__(self):
                return iter([])  # Empty children
        
        node = MockNode()
        with pytest.raises(ValueError, match="IncludeStatementNode should have a filepath"):
            visitor.visit_include_statement(node, [])

    def test_visit_assignment_expr_missing_expression(self):
        """Test visit_assignment_expr with missing expression."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        name = Identifier(name="x", position=Position("", 1, 1))
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="assignment_expr should have an Expression"):
            visitor.visit_assignment_expr(node, [name])

    def test_visit_let_expr_missing_expression(self):
        """Test visit_let_expr with missing expression."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="let_expr should have an Expression body"):
            visitor.visit_let_expr(node, [])

    def test_visit_assert_expr_missing_expression(self):
        """Test visit_assert_expr with missing expression."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="assert_expr should have an Expression body"):
            visitor.visit_assert_expr(node, [])

    def test_visit_echo_expr_missing_expression(self):
        """Test visit_echo_expr with missing expression."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="echo_expr should have an Expression body"):
            visitor.visit_echo_expr(node, [])

    def test_visit_ternary_expr_wrong_count(self):
        """Test visit_ternary_expr with wrong number of expressions."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral
        
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="ternary_expr should have 3 Expression children"):
            visitor.visit_ternary_expr(node, [expr1, expr2])

    def test_visit_string_contents(self):
        """Test visit_string_contents behavior."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            value = "fallback"

        node = MockNode()
        assert visitor.visit_string_contents(node, []) == "fallback"
        assert visitor.visit_string_contents(node, ["a", "b"]) == "b"

    def test_visit_prec_unary_with_node_children(self):
        """Test visit_prec_unary using operator nodes from iterable node."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockOp:
            def __init__(self, rule_name):
                self.rule_name = rule_name

        class MockNode:
            position = 0
            def __iter__(self):
                return iter([MockOp("TOK_BINARY_NOT"), MockOp("TOK_LOGICAL_NOT"), MockOp("expr")])

        node = MockNode()
        expr = NumberLiteral(val=1.0, position=Position("", 1, 1))
        result = visitor.visit_prec_unary(node, [expr])
        assert isinstance(result, BitwiseNotOp)
        assert isinstance(result.expr, LogicalNotOp)

    def test_visit_prec_unary_fallback_ops(self):
        """Test visit_prec_unary fallback with string operators."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0
            def __iter__(self):
                raise TypeError("Cannot iterate")

        node = MockNode()
        expr = NumberLiteral(val=1.0, position=Position("", 1, 1))
        result = visitor.visit_prec_unary(node, ["-", expr])
        assert isinstance(result, UnaryMinusOp)

    def test_visit_prec_multiplication_unknown_operator(self):
        """Test visit_prec_multiplication default multiplication for unknown operator."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        node = MockNode()
        left = NumberLiteral(val=1.0, position=Position("", 1, 1))
        right = NumberLiteral(val=2.0, position=Position("", 1, 1))
        result = visitor.visit_prec_multiplication(node, [left, "?", right])
        assert isinstance(result, MultiplicationOp)

    def test_visit_none_returning_tokens(self):
        """Test visit_* methods that intentionally return None."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        node = MockNode()

        none_methods = [
            visitor.visit_whitespace_only,
            visitor.visit_TOK_LOGICAL_OR,
            visitor.visit_TOK_LOGICAL_AND,
            visitor.visit_TOK_LOGICAL_NOT,
            visitor.visit_TOK_BINARY_OR,
            visitor.visit_TOK_BINARY_AND,
            visitor.visit_TOK_BINARY_NOT,
            visitor.visit_TOK_BINARY_SHIFT_LEFT,
            visitor.visit_TOK_BINARY_SHIFT_RIGHT,
            visitor.visit_TOK_GT,
            visitor.visit_TOK_LT,
            visitor.visit_TOK_GTE,
            visitor.visit_TOK_LTE,
            visitor.visit_TOK_EQUAL,
            visitor.visit_TOK_NOTEQUAL,
            visitor.visit_TOK_QUESTION,
            visitor.visit_TOK_EXPONENT,
            visitor.visit_MOD_SHOW_ONLY,
            visitor.visit_MOD_HIGHLIGHT,
            visitor.visit_MOD_BACKGROUND,
            visitor.visit_MOD_DISABLE,
            visitor.visit_TOK_DQUOTE,
            visitor.visit_TOK_BRACE,
            visitor.visit_TOK_ENDBRACE,
            visitor.visit_TOK_BRACKET,
            visitor.visit_TOK_ENDBRACKET,
            visitor.visit_TOK_COLON,
            visitor.visit_TOK_SEMICOLON,
            visitor.visit_TOK_COMMA,
            visitor.visit_TOK_PERIOD,
            visitor.visit_TOK_PAREN,
            visitor.visit_TOK_ENDPAREN,
            visitor.visit_KWD_MODULE,
            visitor.visit_KWD_FUNCTION,
            visitor.visit_KWD_USE,
            visitor.visit_KWD_INCLUDE,
            visitor.visit_KWD_IF,
            visitor.visit_KWD_ELSE,
            visitor.visit_KWD_FOR,
            visitor.visit_KWD_INTERSECTION_FOR,
            visitor.visit_KWD_LET,
            visitor.visit_KWD_ASSERT,
            visitor.visit_KWD_ECHO,
            visitor.visit_KWD_EACH,
            visitor.visit_TOK_ASSIGN,
            visitor.visit_TOK_SHOW_ONLY,
            visitor.visit_TOK_HIGHLIGHT,
            visitor.visit_TOK_BACKGROUND,
            visitor.visit_TOK_DISABLE,
        ]

        for method in none_methods:
            assert method(node, []) is None

    def test_visit_name_rules(self):
        """Test visit_* name rules return the first child."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        ident = Identifier(name="test", position=Position("", 1, 1))

        assert visitor.visit_module_name(None, [ident]) is ident
        assert visitor.visit_function_name(None, [ident]) is ident
        assert visitor.visit_variable_name(None, [ident]) is ident
        assert visitor.visit_module_instantiation_name(None, [ident]) is ident
        assert visitor.visit_member_name(None, [ident]) is ident
        assert visitor.visit_variable_or_function_name(None, [ident]) is ident
        assert visitor.visit_module_name(None, []) is None

    def test_visit_call_expr_and_suffixes(self):
        """Test visit_call_expr/lookup_expr/member_expr tuple markers."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        arg1 = PositionalArgument(expr=NumberLiteral(val=1.0, position=Position("", 1, 1)), position=Position("", 1, 1))
        arg2 = PositionalArgument(expr=NumberLiteral(val=2.0, position=Position("", 1, 1)), position=Position("", 1, 1))

        assert visitor.visit_call_expr(None, [arg1, arg2]) == ("call", [arg1, arg2])
        index_expr = NumberLiteral(val=1.0, position=Position("", 1, 1))
        assert visitor.visit_lookup_expr(None, [index_expr]) == ("index", index_expr)
        assert visitor.visit_lookup_expr(None, []) == ("index", None)
        member_ident = Identifier(name="x", position=Position("", 1, 1))
        assert visitor.visit_member_expr(None, [member_ident]) == ("member", member_ident)
        assert visitor.visit_member_expr(None, []) == ("member", None)

    def test_visit_vector_expr_wraps_elements(self):
        """Test visit_vector_expr normalizes elements to list."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        elem = NumberLiteral(val=1.0, position=Position("", 1, 1))
        result = visitor.visit_vector_expr(None, [elem])
        assert isinstance(result, ListComprehension)
        assert result.elements == [elem]

        empty = visitor.visit_vector_expr(None, [])
        assert isinstance(empty, ListComprehension)
        assert empty.elements == []

    def test_visit_modular_list_normalization(self):
        """Test modular_* methods normalize assignment/argument lists."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        assignment = Assignment(name=Identifier(name="i", position=Position("", 1, 1)),
                               expr=NumberLiteral(val=1.0, position=Position("", 1, 1)),
                               position=Position("", 1, 1))
        call = ModularCall(name=Identifier(name="cube", position=Position("", 1, 1)),
                           arguments=[], children=[], position=Position("", 1, 1))

        mod_for = visitor.visit_modular_for(None, [assignment, call])
        assert isinstance(mod_for, ModularFor)
        assert mod_for.assignments == [assignment]

        mod_c_for = visitor.visit_modular_c_for(None, [assignment, NumberLiteral(val=1.0, position=Position("", 1, 1)), assignment, call])
        assert isinstance(mod_c_for, ModularCFor)
        assert mod_c_for.initial == [assignment]
        assert mod_c_for.increment == [assignment]

        mod_let = visitor.visit_modular_let(None, [assignment, call])
        assert isinstance(mod_let, ModularLet)
        assert mod_let.assignments == [assignment]
        assert mod_let.children == [call]

        arg = PositionalArgument(expr=NumberLiteral(val=2.0, position=Position("", 1, 1)), position=Position("", 1, 1))
        mod_echo = visitor.visit_modular_echo(None, [arg, call])
        assert isinstance(mod_echo, ModularEcho)
        assert mod_echo.arguments == [arg]
        assert mod_echo.children == [call]

        mod_assert = visitor.visit_modular_assert(None, [arg, call])
        assert isinstance(mod_assert, ModularAssert)
        assert mod_assert.arguments == [arg]
        assert mod_assert.children == [call]

    def test_visit_modular_intersection_for_normalizes_assignments(self):
        """Test modular_intersection_for wraps assignment into list."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        assignment = Assignment(name=Identifier(name="i", position=Position("", 1, 1)),
                               expr=NumberLiteral(val=1.0, position=Position("", 1, 1)),
                               position=Position("", 1, 1))
        call = ModularCall(name=Identifier(name="cube", position=Position("", 1, 1)),
                           arguments=[], children=[], position=Position("", 1, 1))

        mod_for = visitor.visit_modular_intersection_for(None, [assignment, call])
        assert isinstance(mod_for, ModularIntersectionFor)
        assert mod_for.assignments == [assignment]

    def test_visit_modular_intersection_c_for_normalizes_lists(self):
        """Test modular_intersection_c_for wraps init/increment into lists."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        assignment = Assignment(name=Identifier(name="i", position=Position("", 1, 1)),
                               expr=NumberLiteral(val=1.0, position=Position("", 1, 1)),
                               position=Position("", 1, 1))
        condition = BooleanLiteral(val=True, position=Position("", 1, 1))
        call = ModularCall(name=Identifier(name="cube", position=Position("", 1, 1)),
                           arguments=[], children=[], position=Position("", 1, 1))

        mod_c_for = visitor.visit_modular_intersection_c_for(
            None, [assignment, condition, assignment, call]
        )
        assert isinstance(mod_c_for, ModularIntersectionCFor)
        assert mod_c_for.initial == [assignment]
        assert mod_c_for.increment == [assignment]

    def test_visit_modular_call_name_coercion(self):
        """Test modular_call coerces non-Identifier name to Identifier."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        result = visitor.visit_modular_call(None, ["cube", [], []])
        assert isinstance(result.name, Identifier)
        assert result.name.name == "cube"

    def test_visitor_with_file_parameter(self):
        """Test ASTBuilderVisitor with file parameter (backward compatibility)."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser, file="test.scad")
        
        assert visitor.file == "test.scad"
        assert visitor.source_map is not None

    def test_visitor_with_empty_file(self):
        """Test ASTBuilderVisitor with empty file parameter."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser, file="")
        
        assert visitor.file == ""
        assert visitor.source_map is not None

    def test_visit_node_non_iterable(self):
        """Test _visit_node with non-iterable node."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            rule_name = "test_rule"
            # Not iterable
        
        node = MockNode()
        # Should handle gracefully
        result = visitor._visit_node(node)
        assert result == node  # Should pass through if no visit method

    def test_visit_node_no_visit_method(self):
        """Test _visit_node with no visit method."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            rule_name = "unknown_rule"
            def __iter__(self):
                return iter([])
        
        node = MockNode()
        result = visitor._visit_node(node)
        # Should pass through the node itself
        assert result == node

    def test_visit_expr_missing_child(self):
        """Test visit_expr with no children."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="expr should have at least one child"):
            visitor.visit_expr(node, [])

    def test_visit_module_instantiation_missing_child(self):
        """Test visit_module_instantiation with no children."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="module_instantiation should have at least one child"):
            visitor.visit_module_instantiation(node, [])

    def test_visit_single_module_instantiation_missing_child(self):
        """Test visit_single_module_instantiation with no children."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        with pytest.raises(ValueError, match="single_module_instantiation should have at least one child"):
            visitor.visit_single_module_instantiation(node, [])

    def test_visit_child_statement_empty(self):
        """Test visit_child_statement with empty children (semicolon)."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        class MockNode:
            position = 0
        
        node = MockNode()
        result = visitor.visit_child_statement(node, [])
        assert result is None

    def test_visit_statement_variants(self):
        """Test visit_statement with empty, single, and multi children."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        node = MockNode()
        assert visitor.visit_statement(node, []) is None
        assert visitor.visit_statement(node, [1]) == 1
        assert visitor.visit_statement(node, [1, 2]) == [1, 2]

    def test_visit_statement_block_and_empty_statement(self):
        """Test visit_statement_block and visit_empty_statement."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        node = MockNode()
        assert visitor.visit_empty_statement(node, []) == []
        assert visitor.visit_statement_block(node, [1, 2, 3]) == [1, 2, 3]

    def test_visit_toplevel_helpers(self):
        """Test top-level statement helpers and EOF."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        node = MockNode()
        assert visitor.visit_toplevel_statement(node, ["x"]) == "x"
        assert visitor.visit_toplevel_statement_or_comment(node, ["y"]) == "y"
        assert visitor.visit_EOF(node, ["ignored"]) is None
        assert visitor.visit_openscad_language(node, [1, 2]) == [1, 2]

    def test_visit_comment_line_and_multi(self):
        """Test comment visitors strip delimiters."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)

        class MockNode:
            position = 0

        line_node = MockNode()
        line_node.value = "// hello"
        line_comment = visitor.visit_comment_line(line_node, [])
        assert isinstance(line_comment, CommentLine)
        assert line_comment.text == " hello"

        multi_node = MockNode()
        multi_node.value = "/* world */"
        multi_comment = visitor.visit_comment_multi(multi_node, [])
        assert isinstance(multi_comment, CommentSpan)
        assert multi_comment.text == " world "

    def test_visit_prec_equality_fallback(self):
        """Test visit_prec_equality fallback path."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral, EqualityOp
        
        # Create a node that will trigger the fallback
        class MockNode:
            position = 0
            def __iter__(self):
                raise TypeError("Cannot iterate")
        
        node = MockNode()
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        
        result = visitor.visit_prec_equality(node, [expr1, expr2])
        assert isinstance(result, EqualityOp)

    def test_visit_prec_comparison_fallback(self):
        """Test visit_prec_comparison fallback path."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral, LessThanOp
        
        class MockNode:
            position = 0
            def __iter__(self):
                raise TypeError("Cannot iterate")
        
        node = MockNode()
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        
        result = visitor.visit_prec_comparison(node, [expr1, expr2])
        assert isinstance(result, LessThanOp)

    def test_visit_prec_equality_unknown_operator(self):
        """Test visit_prec_equality with unknown operator."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral, EqualityOp
        
        class MockOperator:
            rule_name = "UNKNOWN_OP"
        
        class MockNode:
            position = 0
            def __iter__(self):
                return iter([NumberLiteral(val=1.0, position=Position("", 1, 1)), 
                           MockOperator(),
                           NumberLiteral(val=2.0, position=Position("", 1, 1))])
        
        node = MockNode()
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        
        result = visitor.visit_prec_equality(node, [expr1, expr2])
        # Should default to equality
        assert isinstance(result, EqualityOp)

    def test_visit_prec_comparison_unknown_operator(self):
        """Test visit_prec_comparison with unknown operator."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral, LessThanOp
        
        class MockOperator:
            rule_name = "UNKNOWN_OP"
        
        class MockNode:
            position = 0
            def __iter__(self):
                return iter([NumberLiteral(val=1.0, position=Position("", 1, 1)), 
                           MockOperator(),
                           NumberLiteral(val=2.0, position=Position("", 1, 1))])
        
        node = MockNode()
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        
        result = visitor.visit_prec_comparison(node, [expr1, expr2])
        # Should default to less than
        assert isinstance(result, LessThanOp)

    def test_visit_prec_binary_or_fallback(self):
        """Test visit_prec_binary_or fallback path."""
        parser = getOpenSCADParser()
        visitor = ASTBuilderVisitor(parser)
        
        from openscad_parser.ast.nodes import NumberLiteral, BitwiseOrOp
        
        expr1 = NumberLiteral(val=1.0, position=Position("", 1, 1))
        expr2 = NumberLiteral(val=2.0, position=Position("", 1, 1))
        expr3 = NumberLiteral(val=3.0, position=Position("", 1, 1))
        
        class MockNode:
            position = 0
        
        node = MockNode()
        # Test with mismatched operands/operators (triggers fallback)
        result = visitor.visit_prec_binary_or(node, [expr1, expr2, expr3])
        assert isinstance(result, BitwiseOrOp)
