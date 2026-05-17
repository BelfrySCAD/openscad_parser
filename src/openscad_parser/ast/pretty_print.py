"""Pretty-printer: convert an OpenSCAD AST back to formatted source code."""
from __future__ import annotations
from .nodes import (
    ASTNode, Assignment, FunctionDeclaration, ModuleDeclaration,
    UseStatement, IncludeStatement,
    ModuleInstantiation,
    ModularCall, ModularFor, ModularCFor,
    ModularIntersectionFor, ModularIntersectionCFor,
    ModularLet, ModularEcho, ModularAssert,
    ModularIf, ModularIfElse,
    ModularModifierShowOnly, ModularModifierHighlight,
    ModularModifierBackground, ModularModifierDisable,
    CommentLine, CommentSpan,
)


def to_openscad(nodes: list[ASTNode], indent_width: int = 4) -> str:
    """Convert a list of AST nodes to formatted OpenSCAD source code.

    Args:
        nodes: The AST nodes to format (top-level statements).
        indent_width: Number of spaces per indentation level (default: 4).

    Returns:
        Formatted OpenSCAD source code as a string.
    """
    parts = []
    prev_complex = False
    for node in nodes:
        is_complex = isinstance(node, (ModuleDeclaration, FunctionDeclaration))
        if parts and (is_complex or prev_complex):
            parts.append("")
        parts.append(_fmt_node(node, 0, indent_width))
        prev_complex = is_complex
    return "\n".join(parts)


# --- helpers ---

def _as_list(val) -> list:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _join_str(items) -> str:
    return ", ".join(str(i) for i in items)


def _fmt_node(node: ASTNode, indent: int, w: int) -> str:
    """Format any top-level or block-body node."""
    pad = " " * indent

    if isinstance(node, CommentLine):
        return f"{pad}//{node.text}"
    if isinstance(node, CommentSpan):
        return f"{pad}/*{node.text}*/"
    if isinstance(node, UseStatement):
        return f"{pad}use <{node.filepath.val}>"
    if isinstance(node, IncludeStatement):
        return f"{pad}include <{node.filepath.val}>"
    if isinstance(node, Assignment):
        return f"{pad}{node.name} = {node.expr};"
    if isinstance(node, FunctionDeclaration):
        params = _join_str(node.parameters)
        return f"{pad}function {node.name}({params}) = {node.expr};"
    if isinstance(node, ModuleDeclaration):
        params = _join_str(node.parameters)
        block = _fmt_block(node.children, indent, w)
        return f"{pad}module {node.name}({params}) {block}"
    if isinstance(node, ModuleInstantiation):
        return _fmt_inst(node, indent, w)
    return f"{pad}{node}"  # pragma: no cover


def _fmt_block(nodes: list, indent: int, w: int) -> str:
    """Format a list of nodes as a braced block."""
    pad = " " * indent
    if not nodes:
        return "{}"
    inner = "\n".join(_fmt_node(n, indent + w, w) for n in nodes)
    return "{\n" + inner + "\n" + pad + "}"


def _fmt_child(body, indent: int, w: int) -> str:
    """Format the child body of a module instantiation.

    Returns the tail string appended after the header:
      - ``";"`` when there are no children
      - ``"\\n    child;"`` for a single inline child
      - ``" {\\n    ...\\n}"`` for a block of multiple children
    """
    nodes = _as_list(body)
    pad = " " * indent

    if not nodes:
        return ";"
    if len(nodes) == 1:
        return "\n" + _fmt_inst(nodes[0], indent + w, w)
    inner = "\n".join(_fmt_inst(n, indent + w, w) for n in nodes)
    return " {\n" + inner + "\n" + pad + "}"


def _fmt_inst(node: ModuleInstantiation, indent: int, w: int, prefix: str = "") -> str:
    """Format a ModuleInstantiation node.

    ``prefix`` accumulates modifier characters (``!``, ``#``, ``%``, ``*``)
    so nested modifiers produce e.g. ``!#cube(10);``.
    """
    pad = " " * indent

    # Modifiers: push prefix down to the wrapped node
    if isinstance(node, ModularModifierShowOnly):
        return _fmt_inst(node.child, indent, w, "!" + prefix)
    if isinstance(node, ModularModifierHighlight):
        return _fmt_inst(node.child, indent, w, "#" + prefix)
    if isinstance(node, ModularModifierBackground):
        return _fmt_inst(node.child, indent, w, "%" + prefix)
    if isinstance(node, ModularModifierDisable):
        return _fmt_inst(node.child, indent, w, "*" + prefix)

    if isinstance(node, ModularCall):
        args = _join_str(node.arguments)
        return f"{pad}{prefix}{node.name}({args})" + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularFor):
        assigns = _join_str(_as_list(node.assignments))
        return f"{pad}{prefix}for ({assigns})" + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularCFor):
        init = _join_str(_as_list(node.initial))
        inc = _join_str(_as_list(node.increment))
        return f"{pad}{prefix}for ({init}; {node.condition}; {inc})" + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularIntersectionFor):
        assigns = _join_str(_as_list(node.assignments))
        return f"{pad}{prefix}intersection_for ({assigns})" + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularIntersectionCFor):
        init = _join_str(_as_list(node.initial))
        inc = _join_str(_as_list(node.increment))
        return f"{pad}{prefix}intersection_for ({init}; {node.condition}; {inc})" + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularLet):
        assigns = _join_str(_as_list(node.assignments))
        return f"{pad}{prefix}let ({assigns})" + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularEcho):
        args = _join_str(node.arguments)
        return f"{pad}{prefix}echo({args})" + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularAssert):
        args = _join_str(node.arguments)
        return f"{pad}{prefix}assert({args})" + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularIf):
        header = f"{pad}{prefix}if ({node.condition})"
        return header + _fmt_child(node.true_branch, indent, w)

    if isinstance(node, ModularIfElse):
        header = f"{pad}{prefix}if ({node.condition})"
        true_tail = _fmt_child(node.true_branch, indent, w)
        false_tail = _fmt_child(node.false_branch, indent, w)
        connector = " else" if true_tail.startswith(" {") else f"\n{pad}else"
        return header + true_tail + connector + false_tail

    return f"{pad}{prefix}{node};"  # pragma: no cover
