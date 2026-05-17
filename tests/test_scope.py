"""Tests for scope tracking functionality."""
import pytest
from openscad_parser.ast import (
    getASTfromString, build_scopes, Scope,
    Assignment, FunctionDeclaration, ModuleDeclaration,
    ModularCall, ModularFor, ModularIf, ModularIfElse,
    ModularLet, LetOp, FunctionLiteral, Identifier,
    ModularCFor, ModularEcho, ModularAssert,
    ModularModifierShowOnly, ModularModifierHighlight,
    ModularModifierBackground, ModularModifierDisable,
    ListComprehension, ListCompFor, ListCompCFor, ListCompLet,
    ListCompIf, ListCompIfElse, ListCompEach,
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

    def test_define_and_lookup_variable(self):
        scope = Scope()
        ast = getASTfromString("a = 1;")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, Assignment)
        scope.define_variable("a", n)
        assert scope.lookup_variable("a") is n

    def test_define_and_lookup_function(self):
        scope = Scope()
        ast = getASTfromString("function f(x) = x;")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, FunctionDeclaration)
        scope.define_function("f", n)
        assert scope.lookup_function("f") is n

    def test_define_and_lookup_module(self):
        scope = Scope()
        ast = getASTfromString("module m() {}")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, ModuleDeclaration)
        scope.define_module("m", n)
        assert scope.lookup_module("m") is n

    def test_lookup_variable_in_parent(self):
        parent = Scope()
        ast = getASTfromString("x = 1;")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, Assignment)
        parent.define_variable("x", n)
        child = parent.child_scope()
        assert child.lookup_variable("x") is not None

    def test_lookup_function_in_parent(self):
        parent = Scope()
        ast = getASTfromString("function f() = 1;")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, FunctionDeclaration)
        parent.define_function("f", n)
        child = parent.child_scope()
        assert child.lookup_function("f") is not None

    def test_lookup_module_in_parent(self):
        parent = Scope()
        ast = getASTfromString("module m() {}")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, ModuleDeclaration)
        parent.define_module("m", n)
        child = parent.child_scope()
        assert child.lookup_module("m") is not None

    def test_repr_with_bindings(self):
        scope = Scope()
        ast = getASTfromString("x = 1;")
        assert ast is not None and isinstance(ast, list)
        n = ast[0]
        assert isinstance(n, Assignment)
        scope.define_variable("x", n)
        repr_str = repr(scope)
        assert "x" in repr_str and "vars=" in repr_str


class TestScopeBuilderBasics:
    """Test basic scope-building functionality."""

    def test_build_scopes_convenience(self):
        """build_scopes() returns root scope and attaches scopes to nodes."""
        ast = getASTfromString("a = 1;")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)
        assert isinstance(root, Scope)
        assert root.lookup_variable("a") is not None
        assert ast[0].scope is not None  # type: ignore

    def test_empty_ast(self):
        root = build_scopes([])
        assert isinstance(root, Scope)
        assert root.parent is None

    def test_simple_assignment(self):
        ast = getASTfromString("x = 10;")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        # Variable should be in root scope
        var = root.lookup_variable("x")
        assert var is not None
        assert isinstance(var, Assignment)

    def test_assignment_scope_attached(self):
        ast = getASTfromString("x = 10;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        # Each node should have scope attached
        assignment = ast[0]
        assert hasattr(assignment, 'scope')
        assert assignment.scope is not None  # type: ignore

    def test_multiple_assignments(self):
        ast = getASTfromString("x = 10; y = 20; z = 30;")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        assert root.lookup_variable("x") is not None
        assert root.lookup_variable("y") is not None
        assert root.lookup_variable("z") is not None


class TestFunctionScope:
    """Test function declaration scoping."""

    def test_function_in_root_scope(self):
        ast = getASTfromString("function foo(a) = a + 1;")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        func = root.lookup_function("foo")
        assert func is not None
        assert isinstance(func, FunctionDeclaration)

    def test_function_parameters_in_function_scope(self):
        ast = getASTfromString("function foo(a, b) = a + b;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        func_decl = ast[0]
        # The expression (a + b) should have access to parameters
        expr = func_decl.expr  # type: ignore
        assert expr.scope is not None
        assert expr.scope.lookup_variable("a") is not None
        assert expr.scope.lookup_variable("b") is not None

    def test_function_sees_outer_variables(self):
        ast = getASTfromString("x = 10; function foo(a) = a + x;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr  # type: ignore
        # Function should see outer variable x
        assert expr.scope.lookup_variable("x") is not None

    def test_function_parameter_with_default(self):
        """Parameter with default is in function scope; default expr visited in caller scope."""
        ast = getASTfromString("function foo(x, y = 2) = x + y;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        func_decl = ast[0]
        assert func_decl.expr.scope.lookup_variable("x") is not None  # type: ignore
        assert func_decl.expr.scope.lookup_variable("y") is not None  # type: ignore

    def test_function_parameter_default_visited_in_caller_scope(self):
        """ParameterDeclaration with default: node.default is visited in caller (parent) scope."""
        ast = getASTfromString("function foo(x = 1) = x;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        func_decl = ast[0]
        param = func_decl.parameters[0]  # type: ignore
        assert param.default is not None
        # Default expr is visited in scope.parent; should have a scope attached
        assert param.default.scope is not None  # type: ignore


class TestModuleScope:
    """Test module declaration scoping."""

    def test_module_in_root_scope(self):
        ast = getASTfromString("module foo() { cube(1); }")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        mod = root.lookup_module("foo")
        assert mod is not None
        assert isinstance(mod, ModuleDeclaration)

    def test_module_parameters_in_module_scope(self):
        ast = getASTfromString("module foo(size) { cube(size); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        mod_decl = ast[0]
        # Children should have access to parameters
        if mod_decl.children:  # type: ignore
            child = mod_decl.children[0]  # type: ignore
            assert child.scope.lookup_variable("size") is not None

    def test_module_parameter_with_default(self):
        """Module with default parameter: default expr is visited in caller scope."""
        ast = getASTfromString("module foo(size = 1) { cube(size); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod_decl = ast[0]
        assert len(mod_decl.children) >= 1  # type: ignore
        assert mod_decl.children[0].scope.lookup_variable("size") is not None  # type: ignore

    def test_nested_function_in_module(self):
        ast = getASTfromString("""
            module outer() {
                function helper(x) = x * 2;
                cube(helper(5));
            }
        """)
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        # helper should NOT be in root scope
        assert root.lookup_function("helper") is None

        # But should be in module's scope
        mod_decl = ast[0]
        if mod_decl.children:  # type: ignore
            child = mod_decl.children[0]  # type: ignore
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
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        mod_decl = ast[0]
        # cube(x) should see x due to hoisting
        if mod_decl.children:  # type: ignore
            cube_call = mod_decl.children[0]  # type: ignore
            assert cube_call.scope.lookup_variable("x") is not None


class TestLetExpressions:
    """Test let expression scoping."""

    def test_let_op_creates_scope(self):
        ast = getASTfromString("x = let(a=1, b=2) a + b;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        # The let expression should create a scope with a and b
        assignment = ast[0]
        let_op = assignment.expr  # type: ignore
        assert isinstance(let_op, LetOp)

        # The body should have access to let variables
        body = let_op.body
        assert hasattr(body, 'scope')
        assert body.scope.lookup_variable("a") is not None  # type: ignore
        assert body.scope.lookup_variable("b") is not None  # type: ignore

    def test_let_variables_not_in_outer_scope(self):
        ast = getASTfromString("x = let(a=1) a; y = 2;")
        assert ast is not None and isinstance(ast, list)
        root = build_scopes(ast)

        # a should NOT be in root scope
        assert root.lookup_variable("a") is None


class TestModularConstructs:
    """Test modular construct scoping (for, if, etc.)."""

    def test_modular_for_creates_scope(self):
        ast = getASTfromString("for (i = [1:10]) cube(i);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        for_node = ast[0]
        assert isinstance(for_node, ModularFor)

        # Loop body should have access to loop variable
        body = for_node.body
        if isinstance(body, list):
            body = body[0]
        assert hasattr(body, 'scope')
        assert body.scope.lookup_variable("i") is not None  # type: ignore

    def test_modular_if_creates_scope(self):
        ast = getASTfromString("if (true) { x = 10; cube(x); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        if_node = ast[0]
        assert isinstance(if_node, ModularIf)

    def test_modular_let_creates_scope(self):
        ast = getASTfromString("let(x=10) cube(x);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        let_node = ast[0]
        assert isinstance(let_node, ModularLet)

    def test_modular_if_single_branch(self):
        """ModularIf with single statement (list true_branch with one element)."""
        ast = getASTfromString("if (true) cube(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        if_node = ast[0]
        assert isinstance(if_node, ModularIf)
        assert isinstance(if_node.true_branch, list)
        assert if_node.true_branch[0].scope is not None  # type: ignore

    def test_modular_if_else_single_branches(self):
        """ModularIfElse with single-statement branches (list true/false_branch)."""
        ast = getASTfromString("if (true) cube(1); else sphere(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        if_node = ast[0]
        assert isinstance(if_node, ModularIfElse)
        assert isinstance(if_node.true_branch, list)
        assert isinstance(if_node.false_branch, list)
        assert if_node.true_branch[0].scope is not None  # type: ignore
        assert if_node.false_branch[0].scope is not None  # type: ignore

    def test_modular_for_list_body(self):
        """ModularFor with statement block (list body) or single statement."""
        ast = getASTfromString("for (i = [1:3]) { cube(i); sphere(i); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        for_node = ast[0]
        assert isinstance(for_node, ModularFor)
        body = for_node.body
        first = body[0] if isinstance(body, list) else body
        assert first.scope.lookup_variable("i") is not None  # type: ignore

    def test_modular_c_for(self):
        """ModularCFor creates scope with loop variable."""
        ast = getASTfromString("for (i = 0; i < 3; i = i + 1) cube(i);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        for_node = ast[0]
        assert isinstance(for_node, ModularCFor)
        body = for_node.body[0] if isinstance(for_node.body, list) else for_node.body
        assert body.scope.lookup_variable("i") is not None  # type: ignore

    def test_modular_c_for_block_body(self):
        """ModularCFor with statement block (list body)."""
        ast = getASTfromString("for (i = 0; i < 3; i = i + 1) { cube(i); sphere(i); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        for_node = ast[0]
        assert isinstance(for_node, ModularCFor)
        body = for_node.body
        first = body[0] if isinstance(body, list) else body
        assert first.scope.lookup_variable("i") is not None  # type: ignore

    def test_modular_echo_with_children(self):
        """ModularEcho with child statement gets children scope."""
        ast = getASTfromString('echo("ok") cube(1);')
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        echo_node = ast[0]
        assert isinstance(echo_node, ModularEcho)
        assert len(echo_node.children) >= 1
        assert echo_node.children[0].scope is not None  # type: ignore

    def test_modular_assert_with_children(self):
        """ModularAssert with child statement gets children scope."""
        ast = getASTfromString("assert(true) cube(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        assert_node = ast[0]
        assert isinstance(assert_node, ModularAssert)
        assert len(assert_node.children) >= 1
        assert assert_node.children[0].scope is not None  # type: ignore

    def test_modular_call_empty_children(self):
        """ModularCall with empty block: if node.children is falsy, skip children scope."""
        ast = getASTfromString("cube(1) { }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        call = ast[0]
        assert isinstance(call, ModularCall)
        assert len(call.children) == 0

    def test_modifier_show_only(self):
        ast = getASTfromString("! cube(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod = ast[0]
        assert isinstance(mod, ModularModifierShowOnly)
        assert mod.child.scope is not None  # type: ignore

    def test_modifier_highlight(self):
        ast = getASTfromString("# sphere(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod = ast[0]
        assert isinstance(mod, ModularModifierHighlight)
        assert mod.child.scope is not None  # type: ignore

    def test_modifier_background(self):
        ast = getASTfromString("% cube(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod = ast[0]
        assert isinstance(mod, ModularModifierBackground)
        assert mod.child.scope is not None  # type: ignore

    def test_modifier_disable(self):
        ast = getASTfromString("* cube(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod = ast[0]
        assert isinstance(mod, ModularModifierDisable)
        assert mod.child.scope is not None  # type: ignore


class TestFunctionLiteralRecursion:
    """Test function literal recursion support."""

    def test_function_literal_sees_assigned_variable(self):
        ast = getASTfromString("fn = function(n) n == 0 ? 1 : n * fn(n-1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        assignment = ast[0]
        func_lit = assignment.expr  # type: ignore
        assert isinstance(func_lit, FunctionLiteral)

        # The function body should see 'fn' for recursion
        body = func_lit.body
        assert hasattr(body, 'scope')
        assert body.scope.lookup_variable("fn") is not None  # type: ignore

    def test_function_literal_with_default_parameter(self):
        """Function literal with default parameter visits default in caller scope."""
        ast = getASTfromString("f = function(x = 1) x;")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        assignment = ast[0]
        func_lit = assignment.expr  # type: ignore
        assert func_lit.body.scope.lookup_variable("x") is not None  # type: ignore

    def test_function_literal_in_expression(self):
        """FunctionLiteral in expression (not assigned) gets scope with pending_var=None."""
        ast = getASTfromString("x = (function(a) a)(1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        # FunctionLiteral is inside PrimaryCall; body should see param a
        assign = ast[0]
        pc = assign.expr  # type: ignore
        fl = pc.left  # type: ignore
        assert fl.body.scope.lookup_variable("a") is not None  # type: ignore

    def test_function_literal_in_ternary_rhs_sees_assigned_variable(self):
        """Function literals in a ternary RHS should see the variable being assigned."""
        ast = getASTfromString("a = b ? function(x, n) a(x + n, n - 1) : function(x, n) a(x * n, n - 1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        assignment = ast[0]
        ternary = assignment.expr  # type: ignore
        true_fl = ternary.true_expr  # type: ignore
        false_fl = ternary.false_expr  # type: ignore
        assert isinstance(true_fl, FunctionLiteral)
        assert isinstance(false_fl, FunctionLiteral)
        # Both function bodies should see 'a' for recursion
        assert true_fl.body.scope.lookup_variable("a") is not None  # type: ignore
        assert false_fl.body.scope.lookup_variable("a") is not None  # type: ignore


class TestModularCallChildren:
    """Test that module call children get their own scope."""

    def test_modular_call_with_named_argument(self):
        """ModularCall with NamedArgument visits name and expr."""
        ast = getASTfromString("cube(size=1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        call = ast[0]
        assert isinstance(call, ModularCall)
        assert len(call.arguments) >= 1
        assert call.arguments[0].name.scope is not None  # type: ignore

    def test_primary_call_named_argument_visits_name(self):
        """PrimaryCall with NamedArgument: _visit_node visits arg.name (Identifier)."""
        ast = getASTfromString("a = cube(size=1);")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        assign = ast[0]
        assert hasattr(assign, "expr")
        pc = assign.expr  # type: ignore
        assert hasattr(pc, "arguments") and len(pc.arguments) >= 1  # type: ignore
        arg0 = pc.arguments[0]  # type: ignore
        if hasattr(arg0, "name"):  # NamedArgument
            assert arg0.name.scope is not None  # type: ignore

    def test_modular_call_children_scope(self):
        ast = getASTfromString("""
            module outer() { children(); }
            outer() {
                x = 10;
                cube(x);
            }
        """)
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        # Find the modular call
        mod_call = ast[1]
        assert isinstance(mod_call, ModularCall)

        # Children should have their own scope with x
        if mod_call.children:
            child = mod_call.children[0]
            # x should be visible in children scope due to hoisting
            assert hasattr(child, 'scope')
            assert child.scope.lookup_variable("x") is not None  # type: ignore


class TestScopeLookup:
    """Test scope lookup through parent chain."""

    def test_lookup_function_in_ancestor_scope(self):
        """lookup_function finds function in grandparent when not in parent."""
        ast = getASTfromString("function f() = 1; module m() { g = f(); }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod_decl = ast[1]
        # Assignment g=f() is in module; f is in root
        assign = next(c for c in mod_decl.children if isinstance(c, Assignment))  # type: ignore
        assert assign.scope.lookup_function("f") is not None  # type: ignore

    def test_lookup_module_in_ancestor_scope(self):
        """lookup_module finds module in grandparent when not in parent."""
        ast = getASTfromString("module outer() { function inner() = 1; }")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        mod_decl = ast[0]
        func_decl = next(c for c in mod_decl.children if isinstance(c, FunctionDeclaration))  # type: ignore
        # inner's expr scope: function -> module -> root; outer is in root
        assert func_decl.expr.scope.lookup_module("outer") is not None  # type: ignore

    def test_lookup_in_parent_scope(self):
        ast = getASTfromString("""
            x = 10;
            function foo(a) = a + x;
        """)
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr  # type: ignore

        # x is not in function scope directly, but should be found in parent
        assert expr.scope.lookup_variable("x") is not None
        # a is in function scope directly
        assert expr.scope.lookup_variable("a") is not None

    def test_shadowing(self):
        ast = getASTfromString("""
            x = 10;
            function foo(x) = x + 1;
        """)
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)

        func_decl = ast[1]
        expr = func_decl.expr  # type: ignore

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
        assert ast is not None and isinstance(ast, list)
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


class TestListComprehensionScope:
    """Test list comprehension scoping (ListCompFor, ListCompCFor, ListCompLet, ListCompIf, ListCompIfElse, ListCompEach)."""

    def test_list_comp_for_scope(self):
        ast = getASTfromString("x = [for (i = [0:2]) i];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_for = comp.elements[0]
        assert isinstance(lc_for, ListCompFor)
        assert lc_for.body.scope.lookup_variable("i") is not None  # type: ignore

    def test_list_comp_c_for_scope(self):
        ast = getASTfromString("x = [for (i = 0; i < 3; i = i + 1) i];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_cfor = comp.elements[0]
        assert isinstance(lc_cfor, ListCompCFor)
        assert lc_cfor.body.scope.lookup_variable("i") is not None  # type: ignore

    def test_list_comp_let_scope(self):
        """ListCompLet with body that matches listcomp_elements (nested for)."""
        ast = getASTfromString("x = [let(a = 1) for (i = [0:1]) a];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_let = comp.elements[0]
        assert isinstance(lc_let, ListCompLet)
        assert lc_let.body.scope.lookup_variable("a") is not None  # type: ignore

    def test_list_comp_if_scope(self):
        """ListCompIf (for body) visits condition and true_expr (no new scope)."""
        ast = getASTfromString("x = [for (i = [0:5]) if (i > 0) i];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_for = comp.elements[0]
        assert isinstance(lc_for, ListCompFor)
        assert isinstance(lc_for.body, ListCompIf)
        assert lc_for.body.true_expr.scope is not None  # type: ignore

    def test_list_comp_if_else_scope(self):
        """ListCompIfElse (for body) visits condition, true_expr, false_expr (no new scope)."""
        ast = getASTfromString("x = [for (i = [0:5]) if (i > 0) i else -i];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_for = comp.elements[0]
        assert isinstance(lc_for, ListCompFor)
        assert isinstance(lc_for.body, ListCompIfElse)
        assert lc_for.body.true_expr.scope is not None  # type: ignore
        assert lc_for.body.false_expr.scope is not None  # type: ignore

    def test_list_comp_each_scope(self):
        ast = getASTfromString("x = [each [1, 2, 3]];")
        assert ast is not None and isinstance(ast, list)
        build_scopes(ast)
        comp = ast[0].expr  # type: ignore
        assert isinstance(comp, ListComprehension)
        lc_each = comp.elements[0]
        assert isinstance(lc_each, ListCompEach)
        assert lc_each.body.scope is not None  # type: ignore
