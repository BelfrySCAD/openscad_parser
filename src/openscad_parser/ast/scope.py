"""Scope tracking for OpenSCAD AST nodes.

This module provides classes for tracking lexical scopes in OpenSCAD ASTs,
including variable, function, and module bindings.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, List, Union

if TYPE_CHECKING:
    from .nodes import (
        ASTNode, Assignment, FunctionDeclaration, ModuleDeclaration,
        ParameterDeclaration, ModuleInstantiation, Expression
    )


@dataclass
class Scope:
    """Represents a lexical scope in OpenSCAD.

    A scope tracks variable, function, and module bindings that are visible
    at a particular location in the AST. Scopes form a tree structure through
    parent references, enabling lookup to traverse from inner to outer scopes.

    OpenSCAD has three separate namespaces:
    - Variables: Assignments and parameter declarations
    - Functions: FunctionDeclaration nodes
    - Modules: ModuleDeclaration nodes

    The same name can exist in all three namespaces simultaneously.

    Attributes:
        parent: The enclosing (parent) scope, or None for the root scope.
        variables: Variables defined in this scope (name -> declaring node).
        functions: Functions defined in this scope (name -> FunctionDeclaration).
        modules: Modules defined in this scope (name -> ModuleDeclaration).
    """
    parent: Optional["Scope"] = None
    variables: dict[str, "Assignment | ParameterDeclaration"] = field(default_factory=dict)
    functions: dict[str, "FunctionDeclaration"] = field(default_factory=dict)
    modules: dict[str, "ModuleDeclaration"] = field(default_factory=dict)

    def lookup_variable(self, name: str) -> Optional["Assignment | ParameterDeclaration"]:
        """Look up a variable by name, searching parent scopes.

        Args:
            name: The variable name to look up.

        Returns:
            The Assignment or ParameterDeclaration node that declares the variable,
            or None if not found in this scope or any parent scope.
        """
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup_variable(name)
        return None

    def lookup_function(self, name: str) -> Optional["FunctionDeclaration"]:
        """Look up a function by name, searching parent scopes.

        Args:
            name: The function name to look up.

        Returns:
            The FunctionDeclaration node, or None if not found.
        """
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_function(name)
        return None

    def lookup_module(self, name: str) -> Optional["ModuleDeclaration"]:
        """Look up a module by name, searching parent scopes.

        Args:
            name: The module name to look up.

        Returns:
            The ModuleDeclaration node, or None if not found.
        """
        if name in self.modules:
            return self.modules[name]
        if self.parent:
            return self.parent.lookup_module(name)
        return None

    def define_variable(self, name: str, node: "Assignment | ParameterDeclaration") -> None:
        """Define a variable in this scope.

        Args:
            name: The variable name.
            node: The Assignment or ParameterDeclaration node.
        """
        self.variables[name] = node

    def define_function(self, name: str, node: "FunctionDeclaration") -> None:
        """Define a function in this scope.

        Args:
            name: The function name.
            node: The FunctionDeclaration node.
        """
        self.functions[name] = node

    def define_module(self, name: str, node: "ModuleDeclaration") -> None:
        """Define a module in this scope.

        Args:
            name: The module name.
            node: The ModuleDeclaration node.
        """
        self.modules[name] = node

    def child_scope(self) -> "Scope":
        """Create a new child scope with this scope as parent.

        Returns:
            A new Scope instance with this scope as its parent.
        """
        return Scope(parent=self)

    def __repr__(self) -> str:
        vars_str = ", ".join(self.variables.keys()) if self.variables else "none"
        funcs_str = ", ".join(self.functions.keys()) if self.functions else "none"
        mods_str = ", ".join(self.modules.keys()) if self.modules else "none"
        parent_str = "has parent" if self.parent else "root"
        return f"<Scope({parent_str}) vars=[{vars_str}] funcs=[{funcs_str}] mods=[{mods_str}]>"


class ScopeBuilder:
    """Builds scope information for an OpenSCAD AST.

    The ScopeBuilder walks an AST and attaches a Scope object to each node,
    enabling lookup of what variables, functions, and modules are visible
    at any point in the code.

    Usage:
        ast = getASTfromString("x = 10; cube(x);")
        builder = ScopeBuilder()
        root_scope = builder.build(ast)

        # Now each node has a scope attached
        for node in ast:
            print(node.scope)
    """

    def build(self, ast: List["ASTNode"]) -> Scope:
        """Build scope tree and attach scopes to all AST nodes.

        Args:
            ast: List of top-level AST nodes.

        Returns:
            The root scope containing top-level bindings.
        """
        root_scope = Scope()

        # First pass: collect hoisted declarations at root level
        self._collect_hoisted_declarations(ast, root_scope)

        # Second pass: visit all nodes and assign scopes
        self._visit_nodes(ast, root_scope)

        return root_scope

    def _collect_hoisted_declarations(
        self,
        nodes: List["ASTNode"],
        scope: Scope
    ) -> None:
        """Collect hoisted declarations from a list of nodes.

        In OpenSCAD, assignments, function declarations, and module declarations
        are hoisted within modular sub-blocks. This method scans the nodes and
        adds their bindings to the scope.

        Args:
            nodes: List of AST nodes to scan.
            scope: The scope to add bindings to.
        """
        from .nodes import Assignment, FunctionDeclaration, ModuleDeclaration

        for node in nodes:
            if isinstance(node, Assignment):
                name = node.name.name
                scope.define_variable(name, node)
            elif isinstance(node, FunctionDeclaration):
                name = node.name.name
                scope.define_function(name, node)
            elif isinstance(node, ModuleDeclaration):
                name = node.name.name
                scope.define_module(name, node)

    def _visit_nodes(
        self,
        nodes: List["ASTNode"],
        scope: Scope,
        pending_var: Optional[tuple[str, "Assignment"]] = None
    ) -> None:
        """Visit a list of nodes and assign scopes.

        Args:
            nodes: List of AST nodes to visit.
            scope: The current scope.
            pending_var: Optional (name, node) tuple for a variable that should
                be added to scope after visiting its assignment expression.
        """
        for node in nodes:
            self._visit_node(node, scope, pending_var)
            pending_var = None  # Only applies to first node

    def _visit_node(
        self,
        node: "ASTNode",
        scope: Scope,
        pending_var: Optional[tuple[str, "Assignment"]] = None
    ) -> None:
        """Visit a single node and assign its scope.

        Args:
            node: The AST node to visit.
            scope: The current scope.
            pending_var: Optional (name, node) tuple for a variable that should
                be added to scope for function literals.
        """
        from .nodes import (
            Assignment, FunctionDeclaration, ModuleDeclaration,
            LetOp, ModularLet, ModularIf, ModularIfElse,
            ModularFor, ModularCFor, ModularIntersectionFor, ModularIntersectionCFor,
            ModularCall, ModularEcho, ModularAssert,
            ListCompFor, ListCompCFor, ListCompLet,
            FunctionLiteral, ParameterDeclaration,
            ListComprehension, Expression, ModuleInstantiation,
            PrimaryCall, PrimaryIndex, PrimaryMember,
            TernaryOp, AdditionOp, SubtractionOp, MultiplicationOp, DivisionOp,
            ModuloOp, ExponentOp, LogicalAndOp, LogicalOrOp, LogicalNotOp,
            BitwiseAndOp, BitwiseOrOp, BitwiseNotOp, BitwiseShiftLeftOp, BitwiseShiftRightOp,
            EqualityOp, InequalityOp, GreaterThanOp, GreaterThanOrEqualOp,
            LessThanOp, LessThanOrEqualOp, UnaryMinusOp,
            EchoOp, AssertOp, PositionalArgument, NamedArgument,
            ListCompIf, ListCompIfElse, ListCompEach,
            ModularModifierShowOnly, ModularModifierHighlight,
            ModularModifierBackground, ModularModifierDisable,
            RangeLiteral, Identifier, CommentLine, CommentSpan
        )

        # Assign scope to this node
        node.scope = scope

        # Handle different node types
        if isinstance(node, Assignment):
            # Assignment RHS cannot see the variable being defined
            # Exception: FunctionLiteral can see the variable for recursion
            self._visit_assignment(node, scope)

        elif isinstance(node, FunctionDeclaration):
            self._visit_function_declaration(node, scope)

        elif isinstance(node, ModuleDeclaration):
            self._visit_module_declaration(node, scope)

        elif isinstance(node, LetOp):
            self._visit_let_op(node, scope)

        elif isinstance(node, ModularLet):
            self._visit_modular_let(node, scope)

        elif isinstance(node, ModularIf):
            self._visit_modular_if(node, scope)

        elif isinstance(node, ModularIfElse):
            self._visit_modular_if_else(node, scope)

        elif isinstance(node, (ModularFor, ModularIntersectionFor)):
            self._visit_modular_for(node, scope)

        elif isinstance(node, (ModularCFor, ModularIntersectionCFor)):
            self._visit_modular_c_for(node, scope)

        elif isinstance(node, ModularCall):
            self._visit_modular_call(node, scope)

        elif isinstance(node, (ModularEcho, ModularAssert)):
            self._visit_modular_echo_assert(node, scope)

        elif isinstance(node, ListCompFor):
            self._visit_list_comp_for(node, scope)

        elif isinstance(node, ListCompCFor):
            self._visit_list_comp_c_for(node, scope)

        elif isinstance(node, ListCompLet):
            self._visit_list_comp_let(node, scope)

        elif isinstance(node, FunctionLiteral):
            self._visit_function_literal(node, scope, pending_var)

        elif isinstance(node, ListComprehension):
            # Visit elements
            for elem in node.elements:
                self._visit_node(elem, scope)

        elif isinstance(node, (ListCompIf, ListCompIfElse)):
            # These don't create scopes, just visit children
            self._visit_list_comp_conditional(node, scope)

        elif isinstance(node, ListCompEach):
            self._visit_node(node.body, scope)

        elif isinstance(node, (ModularModifierShowOnly, ModularModifierHighlight,
                               ModularModifierBackground, ModularModifierDisable)):
            self._visit_node(node.child, scope)

        elif isinstance(node, ParameterDeclaration):
            if node.default:
                self._visit_node(node.default, scope)

        elif isinstance(node, (PositionalArgument, NamedArgument)):
            self._visit_node(node.expr, scope)
            if isinstance(node, NamedArgument):
                self._visit_node(node.name, scope)

        elif isinstance(node, PrimaryCall):
            self._visit_node(node.left, scope)
            for arg in node.arguments:
                self._visit_node(arg, scope)

        elif isinstance(node, PrimaryIndex):
            self._visit_node(node.left, scope)
            self._visit_node(node.index, scope)

        elif isinstance(node, PrimaryMember):
            self._visit_node(node.left, scope)
            self._visit_node(node.member, scope)

        elif isinstance(node, TernaryOp):
            self._visit_node(node.condition, scope)
            self._visit_node(node.true_expr, scope)
            self._visit_node(node.false_expr, scope)

        elif isinstance(node, (AdditionOp, SubtractionOp, MultiplicationOp,
                               DivisionOp, ModuloOp, ExponentOp,
                               LogicalAndOp, LogicalOrOp,
                               BitwiseAndOp, BitwiseOrOp,
                               BitwiseShiftLeftOp, BitwiseShiftRightOp,
                               EqualityOp, InequalityOp,
                               GreaterThanOp, GreaterThanOrEqualOp,
                               LessThanOp, LessThanOrEqualOp)):
            self._visit_node(node.left, scope)
            self._visit_node(node.right, scope)

        elif isinstance(node, (LogicalNotOp, BitwiseNotOp, UnaryMinusOp)):
            self._visit_node(node.expr, scope)

        elif isinstance(node, (EchoOp, AssertOp)):
            for arg in node.arguments:
                self._visit_node(arg, scope)
            self._visit_node(node.body, scope)

        elif isinstance(node, RangeLiteral):
            self._visit_node(node.start, scope)
            self._visit_node(node.end, scope)
            self._visit_node(node.step, scope)

        # Leaf nodes (Identifier, literals, comments) just get their scope assigned

    def _visit_assignment(self, node: "Assignment", scope: Scope) -> None:
        """Visit an assignment node.

        The RHS expression cannot see the variable being defined, except
        for function literals which can see it for recursion.
        """
        from .nodes import FunctionLiteral

        # Visit the name identifier
        self._visit_node(node.name, scope)

        # Check if RHS is a FunctionLiteral - if so, it can see the variable
        if isinstance(node.expr, FunctionLiteral):
            # Pass the pending variable to the function literal
            self._visit_function_literal(
                node.expr, scope,
                pending_var=(node.name.name, node)
            )
        else:
            # Regular expression - cannot see the variable being defined
            self._visit_node(node.expr, scope)

    def _visit_function_declaration(self, node: "FunctionDeclaration", scope: Scope) -> None:
        """Visit a function declaration node."""
        # Visit the name in parent scope
        self._visit_node(node.name, scope)

        # Create new scope for function body
        func_scope = scope.child_scope()

        # Add parameters to function scope
        for param in node.parameters:
            param.scope = func_scope
            func_scope.define_variable(param.name.name, param)
            self._visit_node(param.name, func_scope)
            if param.default:
                # Default values are evaluated in caller scope
                self._visit_node(param.default, scope)

        # Visit body expression in function scope
        self._visit_node(node.expr, func_scope)

    def _visit_module_declaration(self, node: "ModuleDeclaration", scope: Scope) -> None:
        """Visit a module declaration node."""
        # Visit the name in parent scope
        self._visit_node(node.name, scope)

        # Create new scope for module body
        mod_scope = scope.child_scope()

        # Add parameters to module scope
        for param in node.parameters:
            param.scope = mod_scope
            mod_scope.define_variable(param.name.name, param)
            self._visit_node(param.name, mod_scope)
            if param.default:
                # Default values are evaluated in caller scope
                self._visit_node(param.default, scope)

        # Collect hoisted declarations from module body
        self._collect_hoisted_declarations(node.children, mod_scope)

        # Visit children in module scope
        self._visit_nodes(node.children, mod_scope)

    def _visit_let_op(self, node: "LetOp", scope: Scope) -> None:
        """Visit a let expression (expression-level)."""
        # Create new scope for let body
        let_scope = scope.child_scope()

        # Add assignments to let scope
        for assignment in node.assignments:
            assignment.scope = let_scope
            let_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, let_scope)
            # Assignment RHS is evaluated in the let scope (can see earlier let vars)
            self._visit_node(assignment.expr, let_scope)

        # Visit body in let scope
        self._visit_node(node.body, let_scope)

    def _visit_modular_let(self, node: "ModularLet", scope: Scope) -> None:
        """Visit a modular let statement."""
        # Create new scope for let body
        let_scope = scope.child_scope()

        # Add assignments to let scope
        for assignment in node.assignments:
            assignment.scope = let_scope
            let_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, let_scope)
            self._visit_node(assignment.expr, let_scope)

        # Collect hoisted declarations from children
        self._collect_hoisted_declarations(node.children, let_scope)

        # Visit children in let scope
        self._visit_nodes(node.children, let_scope)

    def _visit_modular_if(self, node: "ModularIf", scope: Scope) -> None:
        """Visit a modular if statement (no else)."""
        # Condition is in parent scope
        self._visit_node(node.condition, scope)

        # True branch creates its own scope
        true_scope = scope.child_scope()

        # Collect hoisted declarations from true branch
        if isinstance(node.true_branch, list):
            self._collect_hoisted_declarations(node.true_branch, true_scope)
            self._visit_nodes(node.true_branch, true_scope)
        else:
            self._collect_hoisted_declarations([node.true_branch], true_scope)
            self._visit_node(node.true_branch, true_scope)

    def _visit_modular_if_else(self, node: "ModularIfElse", scope: Scope) -> None:
        """Visit a modular if-else statement."""
        # Condition is in parent scope
        self._visit_node(node.condition, scope)

        # True branch creates its own scope
        true_scope = scope.child_scope()
        if isinstance(node.true_branch, list):
            self._collect_hoisted_declarations(node.true_branch, true_scope)
            self._visit_nodes(node.true_branch, true_scope)
        else:
            self._collect_hoisted_declarations([node.true_branch], true_scope)
            self._visit_node(node.true_branch, true_scope)

        # False branch creates its own scope
        false_scope = scope.child_scope()
        if isinstance(node.false_branch, list):
            self._collect_hoisted_declarations(node.false_branch, false_scope)
            self._visit_nodes(node.false_branch, false_scope)
        else:
            self._collect_hoisted_declarations([node.false_branch], false_scope)
            self._visit_node(node.false_branch, false_scope)

    def _visit_modular_for(self, node, scope: Scope) -> None:
        """Visit a modular for loop (or intersection_for)."""
        # Create new scope for loop body
        for_scope = scope.child_scope()

        # Add loop variables to for scope
        for assignment in node.assignments:
            assignment.scope = for_scope
            for_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, for_scope)
            # Loop range is evaluated in parent scope
            self._visit_node(assignment.expr, scope)

        # Collect hoisted declarations from body
        if isinstance(node.body, list):
            self._collect_hoisted_declarations(node.body, for_scope)
            self._visit_nodes(node.body, for_scope)
        else:
            self._collect_hoisted_declarations([node.body], for_scope)
            self._visit_node(node.body, for_scope)

    def _visit_modular_c_for(self, node, scope: Scope) -> None:
        """Visit a modular C-style for loop (or intersection_for)."""
        # Create new scope for loop body
        for_scope = scope.child_scope()

        # Add initial variables to for scope
        for assignment in node.initial:
            assignment.scope = for_scope
            for_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, for_scope)
            self._visit_node(assignment.expr, for_scope)

        # Condition is in for scope
        self._visit_node(node.condition, for_scope)

        # Increment is in for scope
        for assignment in node.increment:
            assignment.scope = for_scope
            self._visit_node(assignment.name, for_scope)
            self._visit_node(assignment.expr, for_scope)

        # Collect hoisted declarations from body
        if isinstance(node.body, list):
            self._collect_hoisted_declarations(node.body, for_scope)
            self._visit_nodes(node.body, for_scope)
        else:
            self._collect_hoisted_declarations([node.body], for_scope)
            self._visit_node(node.body, for_scope)

    def _visit_modular_call(self, node: "ModularCall", scope: Scope) -> None:
        """Visit a modular call (module instantiation)."""
        # Name and arguments are in parent scope
        self._visit_node(node.name, scope)
        for arg in node.arguments:
            self._visit_node(arg, scope)

        # Children create their own scope
        if node.children:
            children_scope = scope.child_scope()
            self._collect_hoisted_declarations(node.children, children_scope)
            self._visit_nodes(node.children, children_scope)

    def _visit_modular_echo_assert(self, node, scope: Scope) -> None:
        """Visit a modular echo or assert statement."""
        # Arguments are in parent scope
        for arg in node.arguments:
            self._visit_node(arg, scope)

        # Children create their own scope
        if node.children:
            children_scope = scope.child_scope()
            self._collect_hoisted_declarations(node.children, children_scope)
            self._visit_nodes(node.children, children_scope)

    def _visit_list_comp_for(self, node: "ListCompFor", scope: Scope) -> None:
        """Visit a list comprehension for loop."""
        # Create new scope for loop body
        for_scope = scope.child_scope()

        # Add loop variables to for scope
        for assignment in node.assignments:
            assignment.scope = for_scope
            for_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, for_scope)
            # Loop range is evaluated in parent scope
            self._visit_node(assignment.expr, scope)

        # Visit body in for scope
        self._visit_node(node.body, for_scope)

    def _visit_list_comp_c_for(self, node: "ListCompCFor", scope: Scope) -> None:
        """Visit a list comprehension C-style for loop."""
        # Create new scope for loop body
        for_scope = scope.child_scope()

        # Add initial variables to for scope
        for assignment in node.initial:
            assignment.scope = for_scope
            for_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, for_scope)
            self._visit_node(assignment.expr, for_scope)

        # Condition is in for scope
        self._visit_node(node.condition, for_scope)

        # Increment is in for scope
        for assignment in node.increment:
            assignment.scope = for_scope
            self._visit_node(assignment.name, for_scope)
            self._visit_node(assignment.expr, for_scope)

        # Visit body in for scope
        self._visit_node(node.body, for_scope)

    def _visit_list_comp_let(self, node: "ListCompLet", scope: Scope) -> None:
        """Visit a list comprehension let expression."""
        # Create new scope for let body
        let_scope = scope.child_scope()

        # Add assignments to let scope
        for assignment in node.assignments:
            assignment.scope = let_scope
            let_scope.define_variable(assignment.name.name, assignment)
            self._visit_node(assignment.name, let_scope)
            self._visit_node(assignment.expr, let_scope)

        # Visit body in let scope
        self._visit_node(node.body, let_scope)

    def _visit_list_comp_conditional(self, node, scope: Scope) -> None:
        """Visit a list comprehension if or if-else (no new scope)."""
        from .nodes import ListCompIf, ListCompIfElse

        self._visit_node(node.condition, scope)
        self._visit_node(node.true_expr, scope)
        if isinstance(node, ListCompIfElse):
            self._visit_node(node.false_expr, scope)

    def _visit_function_literal(
        self,
        node: "FunctionLiteral",
        scope: Scope,
        pending_var: Optional[tuple[str, "Assignment"]] = None
    ) -> None:
        """Visit a function literal (anonymous function).

        Args:
            node: The FunctionLiteral node.
            scope: The current scope.
            pending_var: If set, this variable should be visible in the function
                body (for recursive function literals).
        """
        # Create new scope for function body
        func_scope = scope.child_scope()

        # If there's a pending variable (e.g., fn = function(x) fn(x-1)),
        # add it to the function scope for recursion
        if pending_var:
            name, assignment_node = pending_var
            func_scope.define_variable(name, assignment_node)

        # Add parameters to function scope
        for arg in node.arguments:
            arg.scope = func_scope
            if hasattr(arg, 'name'):
                # ParameterDeclaration
                func_scope.define_variable(arg.name.name, arg)
                self._visit_node(arg.name, func_scope)
                if hasattr(arg, 'default') and arg.default:
                    # Default values are evaluated in caller scope
                    self._visit_node(arg.default, scope)

        # Visit body in function scope
        self._visit_node(node.body, func_scope)


def build_scopes(ast: List["ASTNode"]) -> Scope:
    """Convenience function to build scopes for an AST.

    Args:
        ast: List of top-level AST nodes.

    Returns:
        The root scope containing top-level bindings.
    """
    builder = ScopeBuilder()
    return builder.build(ast)
