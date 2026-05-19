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
    ListCompLet,
    PositionalArgument,
    NamedArgument,
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
        formatted = [_fmt_assign(a, indent + w, w) for a in elem.assignments]
        body = _fmt_list_elem(elem.body, indent + w, w)
        assigns_inline = ", ".join(formatted)
        if any("\n" in fa for fa in formatted) or len(f"for ({assigns_inline})") + indent > _MULTILINE_CHAR_LIMIT:
            assign_lines = (",\n" + inner_pad).join(formatted)
            return f"for (\n{inner_pad}{assign_lines}\n{pad})\n{inner_pad}{body}"
        return f"for ({assigns_inline})\n{inner_pad}{body}"
    if isinstance(elem, ListCompCFor):
        fmt_inits = [_fmt_assign(a, indent + w, w) for a in elem.inits]
        fmt_incrs = [_fmt_assign(a, indent + w, w) for a in elem.incrs]
        inits_str = ", ".join(fmt_inits)
        incrs_str = ", ".join(fmt_incrs)
        cond_str = str(elem.condition)
        body = _fmt_list_elem(elem.body, indent + w, w)
        header = f"for ({inits_str}; {cond_str}; {incrs_str})"
        any_multiline = (
            any("\n" in fa for fa in fmt_inits) or
            any("\n" in fa for fa in fmt_incrs) or
            "\n" in cond_str
        )
        if any_multiline or len(header) + indent > _MULTILINE_CHAR_LIMIT:
            return (
                f"for (\n{inner_pad}{inits_str};\n"
                f"{inner_pad}{cond_str};\n"
                f"{inner_pad}{incrs_str}\n{pad})\n{inner_pad}{body}"
            )
        return f"{header}\n{inner_pad}{body}"
    if isinstance(elem, ListCompLet):
        formatted = [_fmt_assign(a, indent + w, w) for a in elem.assignments]
        body = _fmt_list_elem(elem.body, indent, w)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            return f"let(\n{inner_pad}{assign_lines}\n{pad})\n{pad}{body}"
        assigns = ", ".join(formatted)
        return f"let({assigns})\n{pad}{body}"
    if isinstance(elem, LetOp):
        formatted = [_fmt_assign(a, indent + w, w) for a in elem.assignments]
        body = str(elem.body)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            return f"let(\n{inner_pad}{assign_lines}\n{pad})\n{pad}{body}"
        assigns = ", ".join(formatted)
        return f"let({assigns}) {body}"
    if isinstance(elem, ListComprehension):
        return _fmt_expr(elem, indent, w)
    return str(elem)


def _fmt_multiline_args(head: str, args: list, indent: int, w: int, fmt_fn=str) -> str:
    """Format `head(arg1, arg2, ...)` with each arg on its own line."""
    inner_pad = " " * (indent + w)
    pad = " " * indent
    arg_lines = (",\n" + inner_pad).join(fmt_fn(a) for a in args)
    return f"{head}(\n{inner_pad}{arg_lines}\n{pad})"


def _fmt_assign(assign, indent: int, w: int) -> str:
    """Format an Assignment node, routing its expression through _fmt_expr."""
    return f"{assign.name} = {_fmt_expr(assign.expr, indent, w)}"


def _fmt_argument(arg, indent: int, w: int) -> str:
    """Format a call argument, routing its expression through _fmt_expr."""
    if isinstance(arg, PositionalArgument):
        return _fmt_expr(arg.expr, indent, w)
    if isinstance(arg, NamedArgument):
        return f"{arg.name}={_fmt_expr(arg.expr, indent, w)}"
    return str(arg)


def _fmt_expr(expr, indent: int, w: int) -> str:
    """Format an expression with indent-aware layout for ternary, assert, and echo."""
    pad = " " * indent
    if isinstance(expr, TernaryOp):
        pad2 = " " * (indent + 2)
        def _fmt_branch(branch):
            # Nested ternary: 2 spaces per nesting level
            if isinstance(branch, TernaryOp):
                return _fmt_expr(branch, indent + 2, w)
            # All other expressions: their visual start is 2 chars into "? "/":", "
            # so block content and closing delimiters align to indent + 4
            return _fmt_expr(branch, indent + 4, w)
        return (
            f"{expr.condition}\n"
            f"{pad2}? {_fmt_branch(expr.true_expr)}\n"
            f"{pad2}: {_fmt_branch(expr.false_expr)}"
        )
    if isinstance(expr, AssertOp):
        args = ", ".join(str(a) for a in expr.arguments)
        return f"assert({args})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, EchoOp):
        args = ", ".join(str(a) for a in expr.arguments)
        return f"echo({args})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, LetOp):
        inner_pad = " " * (indent + w)
        formatted = [_fmt_assign(a, indent + w, w) for a in expr.assignments]
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            return (
                f"let(\n{inner_pad}{assign_lines}\n{pad})\n"
                f"{pad}{_fmt_expr(expr.body, indent, w)}"
            )
        assigns = ", ".join(formatted)
        return f"let({assigns})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, PrimaryCall):
        inline = str(expr)
        if len(inline) + indent > _MULTILINE_CHAR_LIMIT:
            return _fmt_multiline_args(
                str(expr.left), expr.arguments, indent, w,
                fmt_fn=lambda a: _fmt_argument(a, indent + w, w),
            )
    if isinstance(expr, ListComprehension):
        inner_pad = " " * (indent + w)
        formatted_elems = [_fmt_list_elem(e, indent + w, w) for e in expr.elements]
        any_multiline = any("\n" in fe for fe in formatted_elems)
        if len(str(expr)) + indent > _MULTILINE_CHAR_LIMIT or any_multiline:
            items = (",\n" + inner_pad).join(formatted_elems)
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
            call = _fmt_multiline_args(
                head, node.arguments, indent, w,
                fmt_fn=lambda a: _fmt_argument(a, indent + w, w),
            )
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
        inner_pad = " " * (indent + w)
        formatted = [_fmt_assign(a, indent + w, w) for a in _as_list(node.assignments)]
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            tail = _fmt_child(node.children, indent, w)
            return f"{pad}{prefix}let (\n{inner_pad}{assign_lines}\n{pad}){tail}"
        assigns = ", ".join(formatted)
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
