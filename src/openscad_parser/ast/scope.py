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


class ScopeTable:
    """Where each node's Scope lives, now that it cannot live in the node.

    A parsed file is shared: an included library is parsed once and handed
    to every file that includes it, which is what makes a second includer of
    BOSL2 cost milliseconds rather than a re-parse. But `include` means
    "share my scope", so the very same node sits in a different scope in
    every file that includes it. A `scope` attribute on the node could only
    hold one of them, and whichever file built its scopes last overwrote the
    others' (openscad_cpp_parser #7/#8, where the same move was made).

    One table per scope-building pass: build_scopes() makes one and hangs it
    on the root it returns (`root.table`), and every Scope created under
    that root shares it. build_scopes_into() records into one the caller
    owns, for a resolution that spans several roots (each `use`d file has a
    root of its own, but they are read back through one evaluation).
    """

    def __init__(self) -> None:
        # Keyed by id(node); the node is kept alongside, both so an id reused
        # after the node is freed never matches and so the node stays alive
        # as long as its entry does.
        self._scopes: dict[int, tuple["ASTNode", "Scope"]] = {}

    def get(self, node: "ASTNode") -> Optional["Scope"]:
        """The scope visible at `node`, or None if this table never saw it."""
        hit = self._scopes.get(id(node))
        return hit[1] if hit is not None and hit[0] is node else None

    def set(self, node: "ASTNode", scope: "Scope") -> None:
        self._scopes[id(node)] = (node, scope)

    def __len__(self) -> int:
        return len(self._scopes)


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
    # Where the nodes built under this scope record theirs: the parent's for
    # a child scope, a fresh one for a root unless one is passed in.
    table: ScopeTable = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.table is None:
            self.table = self.parent.table if self.parent is not None else ScopeTable()

    def scope_of(self, node: "ASTNode") -> Optional["Scope"]:
        """The scope visible at `node`, as recorded by the pass that built
        this scope: `root.scope_of(node)` after `root = build_scopes(ast)`."""
        return self.table.get(node)

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
    build_scope() on each node so every node in the tree gets its scope
    recorded -- in `root.table`, read back with `root.scope_of(node)`.

    Args:
        ast: List of top-level AST nodes.

    Returns:
        The root scope containing top-level bindings.
    """
    return build_scopes_into(ast, ScopeTable())


def build_scopes_into(ast: List["ASTNode"], table: ScopeTable) -> Scope:
    """build_scopes(), recording into a table the caller owns, which several
    roots may share -- one per `use`d file, read back through one evaluation.
    """
    from .nodes import Assignment, FunctionDeclaration, ModuleDeclaration

    root_scope = Scope(table=table)

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
