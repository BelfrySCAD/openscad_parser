"""Pretty-printer: convert an OpenSCAD AST back to formatted source code."""
from __future__ import annotations
from .nodes import (
    ASTNode, Assignment, FunctionDeclaration, ModuleDeclaration,
    UseStatement, IncludeStatement,
    ModuleInstantiation,
    ModularCall, ModularFor,
    ModularIntersectionFor,
    ModularLet, ModularEcho, ModularAssert,
    ModularIf, ModularIfElse,
    ModularModifierShowOnly, ModularModifierHighlight,
    ModularModifierBackground, ModularModifierDisable,
    CommentLine, CommentSpan,
    TernaryOp,
    EchoOp,
    AssertOp,
    LetOp,
    PrimaryCall,
    ListComprehension,
    ListCompFor,
    ListCompCFor,
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


# Line length beyond which call arguments are formatted one-per-line.
_MULTILINE_CHAR_LIMIT = 100

# --- helpers ---

def _as_list(val) -> list:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _join_str(items) -> str:
    return ", ".join(str(i) for i in items)


def _fmt_list_elem(elem, indent: int, w: int) -> str:
    """Format a list comprehension element, placing the body on a new line for for loops."""
    pad = " " * indent
    inner_pad = " " * (indent + w)
    if isinstance(elem, ListCompFor):
        assigns_inline = ", ".join(str(a) for a in elem.assignments)
        body = _fmt_list_elem(elem.body, indent + w, w)
        if len(f"for ({assigns_inline})") + indent > _MULTILINE_CHAR_LIMIT:
            assign_lines = (",\n" + inner_pad).join(str(a) for a in elem.assignments)
            return f"for (\n{inner_pad}{assign_lines}\n{pad})\n{inner_pad}{body}"
        return f"for ({assigns_inline})\n{inner_pad}{body}"
    if isinstance(elem, ListCompCFor):
        inits = ", ".join(str(a) for a in elem.inits)
        incrs = ", ".join(str(a) for a in elem.incrs)
        body = _fmt_list_elem(elem.body, indent + w, w)
        return f"for ({inits}; {elem.condition}; {incrs})\n{inner_pad}{body}"
    return str(elem)


def _fmt_multiline_args(head: str, args: list, indent: int, w: int) -> str:
    """Format `head(arg1, arg2, ...)` with each arg on its own line."""
    inner_pad = " " * (indent + w)
    pad = " " * indent
    arg_lines = (",\n" + inner_pad).join(str(a) for a in args)
    return f"{head}(\n{inner_pad}{arg_lines}\n{pad})"


def _fmt_expr(expr, indent: int, w: int) -> str:
    """Format an expression with indent-aware layout for ternary, assert, and echo."""
    pad = " " * indent
    if isinstance(expr, TernaryOp):
        pad2 = " " * (indent + 2)
        return (
            f"{expr.condition}\n"
            f"{pad2}? {_fmt_expr(expr.true_expr, indent + 2, w)}\n"
            f"{pad2}: {_fmt_expr(expr.false_expr, indent + 2, w)}"
        )
    if isinstance(expr, AssertOp):
        args = ", ".join(str(a) for a in expr.arguments)
        return f"assert({args})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, EchoOp):
        args = ", ".join(str(a) for a in expr.arguments)
        return f"echo({args})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, LetOp):
        inner_pad = " " * (indent + w)
        if len(expr.assignments) <= 1:
            assigns = ", ".join(str(a) for a in expr.assignments)
            return f"let({assigns})\n{pad}{_fmt_expr(expr.body, indent, w)}"
        else:
            assign_lines = (",\n" + inner_pad).join(str(a) for a in expr.assignments)
            return (
                f"let(\n{inner_pad}{assign_lines}\n{pad})\n"
                f"{pad}{_fmt_expr(expr.body, indent, w)}"
            )
    if isinstance(expr, PrimaryCall):
        inline = str(expr)
        if len(inline) + indent > _MULTILINE_CHAR_LIMIT:
            return _fmt_multiline_args(str(expr.left), expr.arguments, indent, w)
    if isinstance(expr, ListComprehension):
        inline = str(expr)
        if len(inline) + indent > _MULTILINE_CHAR_LIMIT:
            inner_pad = " " * (indent + w)
            pad = " " * indent
            items = (",\n" + inner_pad).join(_fmt_list_elem(e, indent + w, w) for e in expr.elements)
            return f"[\n{inner_pad}{items}\n{pad}]"
    return str(expr)


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
        return f"{pad}{node.name} = {_fmt_expr(node.expr, indent, w)};"
    if isinstance(node, FunctionDeclaration):
        head = f"{pad}function {node.name}"
        params_inline = _join_str(node.parameters)
        expr_pad = " " * (indent + w)
        if len(f"{head}({params_inline}) =") > _MULTILINE_CHAR_LIMIT:
            param_block = _fmt_multiline_args(head, node.parameters, indent, w)
            return f"{param_block} =\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
        return f"{head}({params_inline}) =\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
    if isinstance(node, ModuleDeclaration):
        head = f"{pad}module {node.name}"
        params_inline = _join_str(node.parameters)
        block = _fmt_block(node.children, indent, w)
        if len(f"{head}({params_inline})") > _MULTILINE_CHAR_LIMIT:
            param_block = _fmt_multiline_args(head, node.parameters, indent, w)
            return f"{param_block} {block}"
        return f"{head}({params_inline}) {block}"
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
        head = f"{pad}{prefix}{node.name}"
        inline = f"{head}({_join_str(node.arguments)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT:
            call = _fmt_multiline_args(head, node.arguments, indent, w)
        else:
            call = inline
        return call + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularFor):
        assigns = _join_str(_as_list(node.assignments))
        return f"{pad}{prefix}for ({assigns})" + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularIntersectionFor):
        assigns = _join_str(_as_list(node.assignments))
        return f"{pad}{prefix}intersection_for ({assigns})" + _fmt_child(node.body, indent, w)

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
