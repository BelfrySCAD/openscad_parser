"""Tests for scope tracking functionality."""
import pytest
from openscad_parser.ast import (
    getASTfromString, build_scopes, Scope, ScopeBuilder,
    Assignment, FunctionDeclaration, ModuleDeclaration,
    ModularCall, ModularFor, ModularIf, ModularIfElse,
    ModularLet, LetOp, FunctionLiteral, Identifier
)


class TestScopeBasics:
    """Test basic Scope class functionality."""

    def test_empty_scope(self):
        scope = Scope()
        assert scope.parent is None
        assert scope.variables == {}
        assert scope.functions == {}
        assert scope.modules == {}

    def test_lookup_variable_not_found(self):
        scope = Scope()
        assert scope.lookup_variable("x") is None

    def test_lookup_function_not_found(self):
        scope = Scope()
        assert scope.lookup_function("foo") is None

    def test_lookup_module_not_found(self):
        scope = Scope()
        assert scope.lookup_module("bar") is None

    def test_child_scope(self):
        parent = Scope()
        child = parent.child_scope()
        assert child.parent is parent

    def test_repr(self):
        scope = Scope()
        repr_str = repr(scope)
        assert "root" in repr_str


class TestScopeBuilderBasics:
    """Test basic ScopeBuilder functionality."""

    def test_empty_ast(self):
        builder = ScopeBuilder()
        root = builder.build([])
        assert isinstance(root, Scope)
        assert root.parent is None

    def test_simple_assignment(self):
        ast = getASTfromString("x = 10;")
        root = build_scopes(ast)

        # Variable should be in root scope
        var = root.lookup_variable("x")
        assert var is not None
        assert isinstance(var, Assignment)

    def test_assignment_scope_attached(self):
        ast = getASTfromString("x = 10;")
        build_scopes(ast)

        # Each node should have scope attached
        assignment = ast[0]
        assert hasattr(assignment, 'scope')
        assert assignment.scope is not None

    def test_multiple_assignments(self):
        ast = getASTfromString("x = 10; y = 20; z = 30;")
        root = build_scopes(ast)

        assert root.lookup_variable("x") is not None
        assert root.lookup_variable("y") is not None
        assert root.lookup_variable("z") is not None


class TestFunctionScope:
    """Test function declaration scoping."""

    def test_function_in_root_scope(self):
        ast = getASTfromString("function foo(a) = a + 1;")
        root = build_scopes(ast)

        func = root.lookup_function("foo")
        assert func is not None
        assert isinstance(func, FunctionDeclaration)

    def test_function_parameters_in_function_scope(self):
        ast = getASTfromString("function foo(a, b) = a + b;")
        build_scopes(ast)

        func_decl = ast[0]
        # The expression (a + b) should have access to parameters
        expr = func_decl.expr
        assert expr.scope is not None
        assert expr.scope.lookup_variable("a") is not None
        assert expr.scope.lookup_variable("b") is not None

    def test_function_sees_outer_variables(self):
        ast = getASTfromString("x = 10; function foo(a) = a + x;")
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr
        # Function should see outer variable x
        assert expr.scope.lookup_variable("x") is not None


class TestModuleScope:
    """Test module declaration scoping."""

    def test_module_in_root_scope(self):
        ast = getASTfromString("module foo() { cube(1); }")
        root = build_scopes(ast)

        mod = root.lookup_module("foo")
        assert mod is not None
        assert isinstance(mod, ModuleDeclaration)

    def test_module_parameters_in_module_scope(self):
        ast = getASTfromString("module foo(size) { cube(size); }")
        build_scopes(ast)

        mod_decl = ast[0]
        # Children should have access to parameters
        if mod_decl.children:
            child = mod_decl.children[0]
            assert child.scope.lookup_variable("size") is not None

    def test_nested_function_in_module(self):
        ast = getASTfromString("""
            module outer() {
                function helper(x) = x * 2;
                cube(helper(5));
            }
        """)
        root = build_scopes(ast)

        # helper should NOT be in root scope
        assert root.lookup_function("helper") is None

        # But should be in module's scope
        mod_decl = ast[0]
        if mod_decl.children:
            child = mod_decl.children[0]
            assert child.scope.lookup_function("helper") is not None


class TestHoisting:
    """Test hoisting behavior in modular scopes."""

    def test_assignment_hoisted_in_module(self):
        ast = getASTfromString("""
            module foo() {
                cube(x);
                x = 10;
            }
        """)
        build_scopes(ast)

        mod_decl = ast[0]
        # cube(x) should see x due to hoisting
        if mod_decl.children:
            cube_call = mod_decl.children[0]
            assert cube_call.scope.lookup_variable("x") is not None


class TestLetExpressions:
    """Test let expression scoping."""

    def test_let_op_creates_scope(self):
        ast = getASTfromString("x = let(a=1, b=2) a + b;")
        build_scopes(ast)

        # The let expression should create a scope with a and b
        assignment = ast[0]
        let_op = assignment.expr
        assert isinstance(let_op, LetOp)

        # The body should have access to let variables
        body = let_op.body
        assert body.scope.lookup_variable("a") is not None
        assert body.scope.lookup_variable("b") is not None

    def test_let_variables_not_in_outer_scope(self):
        ast = getASTfromString("x = let(a=1) a; y = 2;")
        root = build_scopes(ast)

        # a should NOT be in root scope
        assert root.lookup_variable("a") is None


class TestModularConstructs:
    """Test modular construct scoping (for, if, etc.)."""

    def test_modular_for_creates_scope(self):
        ast = getASTfromString("for (i = [1:10]) cube(i);")
        build_scopes(ast)

        for_node = ast[0]
        assert isinstance(for_node, ModularFor)

        # Loop body should have access to loop variable
        body = for_node.body
        if isinstance(body, list):
            body = body[0]
        assert body.scope.lookup_variable("i") is not None

    def test_modular_if_creates_scope(self):
        ast = getASTfromString("if (true) { x = 10; cube(x); }")
        build_scopes(ast)

        if_node = ast[0]
        assert isinstance(if_node, ModularIf)

    def test_modular_let_creates_scope(self):
        ast = getASTfromString("let(x=10) cube(x);")
        build_scopes(ast)

        let_node = ast[0]
        assert isinstance(let_node, ModularLet)


class TestFunctionLiteralRecursion:
    """Test function literal recursion support."""

    def test_function_literal_sees_assigned_variable(self):
        ast = getASTfromString("fn = function(n) n == 0 ? 1 : n * fn(n-1);")
        build_scopes(ast)

        assignment = ast[0]
        func_lit = assignment.expr
        assert isinstance(func_lit, FunctionLiteral)

        # The function body should see 'fn' for recursion
        body = func_lit.body
        assert body.scope.lookup_variable("fn") is not None


class TestModularCallChildren:
    """Test that module call children get their own scope."""

    def test_modular_call_children_scope(self):
        ast = getASTfromString("""
            module outer() { children(); }
            outer() {
                x = 10;
                cube(x);
            }
        """)
        build_scopes(ast)

        # Find the modular call
        mod_call = ast[1]
        assert isinstance(mod_call, ModularCall)

        # Children should have their own scope with x
        if mod_call.children:
            child = mod_call.children[0]
            # x should be visible in children scope due to hoisting
            assert child.scope.lookup_variable("x") is not None


class TestScopeLookup:
    """Test scope lookup through parent chain."""

    def test_lookup_in_parent_scope(self):
        ast = getASTfromString("""
            x = 10;
            function foo(a) = a + x;
        """)
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr

        # x is not in function scope directly, but should be found in parent
        assert expr.scope.lookup_variable("x") is not None
        # a is in function scope directly
        assert expr.scope.lookup_variable("a") is not None

    def test_shadowing(self):
        ast = getASTfromString("""
            x = 10;
            function foo(x) = x + 1;
        """)
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr

        # x in function scope should be the parameter, not global
        x_binding = expr.scope.lookup_variable("x")
        assert x_binding is not None
        # It should be the parameter, which is in the local scope
        assert "x" in expr.scope.variables


class TestThreeNamespaces:
    """Test that three namespaces are independent."""

    def test_same_name_in_all_namespaces(self):
        ast = getASTfromString("""
            thing = 10;
            function thing() = 20;
            module thing() { cube(1); }
        """)
        root = build_scopes(ast)

        assert root.lookup_variable("thing") is not None
        assert root.lookup_function("thing") is not None
        assert root.lookup_module("thing") is not None

        # They should all be different nodes
        var = root.lookup_variable("thing")
        func = root.lookup_function("thing")
        mod = root.lookup_module("thing")

        assert isinstance(var, Assignment)
        assert isinstance(func, FunctionDeclaration)
        assert isinstance(mod, ModuleDeclaration)
