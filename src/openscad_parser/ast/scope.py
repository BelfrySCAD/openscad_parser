"""Scope tracking for OpenSCAD AST nodes.

This module provides the Scope class for representing lexical scopes in
OpenSCAD ASTs, and the build_scopes() convenience function that drives
scope population by calling build_scope() on each top-level AST node.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .nodes import (
        ASTNode, Assignment,
        FunctionDeclaration,
        ModuleDeclaration,
        ParameterDeclaration,
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
        """Look up a variable by name, searching parent scopes."""
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup_variable(name)
        return None

    def lookup_function(self, name: str) -> Optional["FunctionDeclaration"]:
        """Look up a function by name, searching parent scopes."""
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_function(name)
        return None

    def lookup_module(self, name: str) -> Optional["ModuleDeclaration"]:
        """Look up a module by name, searching parent scopes."""
        if name in self.modules:
            return self.modules[name]
        if self.parent:
            return self.parent.lookup_module(name)
        return None

    def define_variable(self, name: str, node: "Assignment | ParameterDeclaration") -> None:
        """Define a variable in this scope."""
        self.variables[name] = node

    def define_function(self, name: str, node: "FunctionDeclaration") -> None:
        """Define a function in this scope."""
        self.functions[name] = node

    def define_module(self, name: str, node: "ModuleDeclaration") -> None:
        """Define a module in this scope."""
        self.modules[name] = node

    def child_scope(self) -> "Scope":
        """Create a new child scope with this scope as parent."""
        return Scope(parent=self)

    def __repr__(self) -> str:
        vars_str = ", ".join(self.variables.keys()) if self.variables else "none"
        funcs_str = ", ".join(self.functions.keys()) if self.functions else "none"
        mods_str = ", ".join(self.modules.keys()) if self.modules else "none"
        parent_str = "has parent" if self.parent else "root"
        return f"<Scope({parent_str}) vars=[{vars_str}] funcs=[{funcs_str}] mods=[{mods_str}]>"


def build_scopes(ast: List["ASTNode"]) -> Scope:
    """Build scope tree for a list of top-level AST nodes.

    Creates a root scope, hoists top-level declarations into it, then calls
    build_scope() on each node so every node in the tree gets its scope set.

    Args:
        ast: List of top-level AST nodes.

    Returns:
        The root scope containing top-level bindings.
    """
    from .nodes import Assignment, FunctionDeclaration, ModuleDeclaration

    root_scope = Scope()

    # Hoist top-level declarations so all siblings can see each other
    for node in ast:
        if isinstance(node, Assignment):
            root_scope.define_variable(node.name.name, node)
        elif isinstance(node, FunctionDeclaration):
            root_scope.define_function(node.name.name, node)
        elif isinstance(node, ModuleDeclaration):
            root_scope.define_module(node.name.name, node)

    for node in ast:
        node.build_scope(root_scope)

    return root_scope
