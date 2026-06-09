"""Pretty-printer: convert an OpenSCAD AST back to formatted source code."""
from __future__ import annotations
from .nodes import (
    ASTNode, Assignment, FunctionDeclaration, ModuleDeclaration, ParameterDeclaration,
    UseStatement, IncludeStatement,
    ModuleInstantiation,
    ModularCall, ModularFor,
    ModularIntersectionFor,
    ModularLet, ModularEcho, ModularAssert,
    ModularIf, ModularIfElse,
    ModularModifierShowOnly, ModularModifierHighlight,
    ModularModifierBackground, ModularModifierDisable,
    BlankLine,
    CommentLine,
    CommentSpan,
    TernaryOp,
    EchoOp,
    AssertOp,
    LetOp,
    UndefinedLiteral,
    CommentedExpr,
    PrimaryCall,
    ListComprehension,
    ListCompFor,
    ListCompCFor,
    ListCompLet,
    ListCompIf,
    ListCompIfElse,
    ListCompEach,
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
        is_blank = isinstance(node, BlankLine)
        if parts and prev_complex and not is_blank:
            parts.append("")
            parts.append("")
        parts.append(_fmt_node(node, 0, indent_width))
        if not is_blank:
            prev_complex = is_complex
    return _coalesce_paren_bracket("\n".join(parts))


def _coalesce_paren_bracket(text: str) -> str:
    """Join consecutive lines where one is a bare ')' and the next starts with '['."""
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        if (
            i + 1 < len(lines)
            and lines[i].strip() == ")"
            and lines[i + 1].lstrip().startswith("[")
        ):
            indent = len(lines[i]) - len(lines[i].lstrip())
            result.append(" " * indent + ") " + lines[i + 1].lstrip())
            i += 2
        else:
            result.append(lines[i])
            i += 1
    return "\n".join(result)


# Line length beyond which call arguments are formatted one-per-line.
_MULTILINE_CHAR_LIMIT = 80

_BINARY_OP_SYMBOLS = {
    'AdditionOp': '+', 'SubtractionOp': '-',
    'MultiplicationOp': '*', 'DivisionOp': '/', 'ModuloOp': '%',
    'ExponentOp': '^',
    'BitwiseAndOp': '&', 'BitwiseOrOp': '|',
    'BitwiseShiftLeftOp': '<<', 'BitwiseShiftRightOp': '>>',
    'LogicalAndOp': '&&', 'LogicalOrOp': '||',
    'EqualityOp': '==', 'InequalityOp': '!=',
    'GreaterThanOp': '>', 'GreaterThanOrEqualOp': '>=',
    'LessThanOp': '<', 'LessThanOrEqualOp': '<=',
}

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
        body = _fmt_expr(elem.body, indent, w)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            return f"let(\n{inner_pad}{assign_lines}\n{pad})\n{pad}{body}"
        assigns = ", ".join(formatted)
        inline = f"let({assigns}) {body}"
        if "\n" in body or len(inline) + indent > _MULTILINE_CHAR_LIMIT:
            return f"let({assigns})\n{pad}{body}"
        return inline
    if isinstance(elem, ListComprehension):
        return _fmt_expr(elem, indent, w)
    if isinstance(elem, ListCompIf):
        cond = str(elem.condition)
        body = _fmt_list_elem(elem.true_expr, indent + w, w)
        return f"if ({cond})\n{inner_pad}{body}"
    if isinstance(elem, ListCompIfElse):
        cond = str(elem.condition)
        true_body = _fmt_list_elem(elem.true_expr, indent + w, w)
        false_body = _fmt_list_elem(elem.false_expr, indent + w, w)
        return f"if ({cond})\n{inner_pad}{true_body}\n{pad}else\n{inner_pad}{false_body}"
    if isinstance(elem, ListCompEach):
        body = _fmt_list_elem(elem.body, indent, w)
        return f"each {body}"
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


def _fmt_ternary_chain(expr: TernaryOp, indent: int, w: int) -> str:
    """Format a right-chain of ternaries with flat ? / : alignment.

    All ': ' connectors stay at the same indent column as the conditions;
    each true branch is on its own line at indent+w.  The '?' moves to
    the end of the condition line rather than the beginning of the true-branch.

        cond1?
            true1
        : cond2?
            true2
        : final_else
    """
    pad = " " * indent
    inner_pad = " " * (indent + w)
    parts = []
    node = expr
    while isinstance(node, TernaryOp):
        parts.append((node.condition, node.true_expr))
        node = node.false_expr
        # step through a CommentedExpr wrapper on the next ternary
        if isinstance(node, CommentedExpr) and isinstance(node.expr, TernaryOp):
            node = node.expr
    final = node
    lines = []
    for i, (cond, true_expr) in enumerate(parts):
        true_str = _fmt_expr(true_expr, indent + w, w)
        prefix = "" if i == 0 else f"{pad}: "
        lines.append(f"{prefix}{cond} ?\n{inner_pad}{true_str}")
    lines.append(f"{pad}: {_fmt_expr(final, indent + w, w)}")
    return "\n".join(lines)


def _fmt_expr(expr, indent: int, w: int) -> str:
    """Format an expression with indent-aware layout for ternary, assert, and echo."""
    pad = " " * indent
    if isinstance(expr, CommentedExpr):
        if any(isinstance(c, CommentLine) for c in expr.leading_comments):
            # Line comments must end their line; split at last CommentLine.
            inner_pad = " " * indent
            last_ll = max(i for i, c in enumerate(expr.leading_comments) if isinstance(c, CommentLine))
            line_part = expr.leading_comments[:last_ll + 1]
            inline_part = expr.leading_comments[last_ll + 1:]
            body_parts = [str(c) for c in inline_part]
            body_parts.append(_fmt_expr(expr.expr, indent, w))
            body_parts.extend(str(c) for c in expr.trailing_comments)
            body = " ".join(body_parts)
            all_lines = [str(c) for c in line_part] + [body]
            return "\n".join([all_lines[0]] + [f"{inner_pad}{l}" for l in all_lines[1:]])
        parts = [str(c) for c in expr.leading_comments]
        parts.append(_fmt_expr(expr.expr, indent, w))
        parts.extend(str(c) for c in expr.trailing_comments)
        return " ".join(parts)
    if isinstance(expr, TernaryOp):
        # Right-chain of ternaries → flat cascade format
        # Unwrap CommentedExpr on the false branch for chain detection
        false_inner = expr.false_expr.expr if isinstance(expr.false_expr, CommentedExpr) else expr.false_expr
        if isinstance(false_inner, TernaryOp):
            return _fmt_ternary_chain(expr, indent, w)
        pad2 = " " * (indent + w)
        def _fmt_branch(branch):
            if isinstance(branch, TernaryOp):
                return _fmt_expr(branch, indent + w, w)
            # Branch content visually starts 2 chars into "? "/":", so block
            # content and closing delimiters align to indent + w + 2
            return _fmt_expr(branch, indent + w + 2, w)
        return (
            f"{expr.condition}\n"
            f"{pad2}? {_fmt_branch(expr.true_expr)}\n"
            f"{pad2}: {_fmt_branch(expr.false_expr)}"
        )
    if isinstance(expr, AssertOp):
        args = ", ".join(str(a) for a in expr.arguments)
        if isinstance(expr.body, UndefinedLiteral):
            return f"assert({args})"
        return f"assert({args})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, EchoOp):
        args = ", ".join(str(a) for a in expr.arguments)
        if isinstance(expr.body, UndefinedLiteral):
            return f"echo({args})"
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
    # Binary op where the left operand is a multiline list: keep [ on the
    # first line and append " op rhs" to the closing ] line.
    if hasattr(expr, 'left') and hasattr(expr, 'right'):
        left_fmt = _fmt_expr(expr.left, indent, w)
        if left_fmt.startswith("[\n"):
            op = _BINARY_OP_SYMBOLS.get(type(expr).__name__)
            if op is not None:
                right_fmt = _fmt_expr(expr.right, indent, w)
                return f"{left_fmt} {op} {right_fmt}"
    if isinstance(expr, ListComprehension):
        inner_pad = " " * (indent + w)
        # A leading CommentLine on element N was written after element N-1's comma
        # in the source ("elem, // note\n next"). Render it as a trailing comment on
        # N-1's line (after the comma), not as a standalone line before N.
        from dataclasses import replace as _dc_replace
        def _split_lcs(e):
            """Return (leading_CommentLines, element_without_those_CommentLines)."""
            if isinstance(e, CommentedExpr):
                lcs = [c for c in e.leading_comments if isinstance(c, CommentLine)]
                if lcs:
                    rest = [c for c in e.leading_comments if not isinstance(c, CommentLine)]
                    cleaned = (e.expr if not rest and not e.trailing_comments
                               else _dc_replace(e, leading_comments=rest))
                    return lcs, cleaned
            return [], e
        splits = [_split_lcs(e) for e in expr.elements]
        has_line_comment = any(lcs for lcs, _ in splits)
        formatted = [_fmt_list_elem(cleaned, indent + w, w) for _, cleaned in splits]
        any_multiline = has_line_comment or any("\n" in fe for fe in formatted)
        if not any_multiline:
            inline = f"[{', '.join(formatted)}]"
            if len(inline) + indent <= _MULTILINE_CHAR_LIMIT:
                return inline
        lines = []
        for i, ((lcs, _), elem_str) in enumerate(zip(splits, formatted)):
            comma = "" if i == len(expr.elements) - 1 else ","
            if lcs:
                # Append the comment(s) to the previous element's line, after its comma
                comment_str = "  " + "  ".join(str(c) for c in lcs)
                if lines:
                    lines[-1] += comment_str
                else:
                    for c in lcs:
                        lines.append(f"{inner_pad}{c}")
            lines.append(f"{inner_pad}{elem_str}{comma}")
        return "[\n" + "\n".join(lines) + f"\n{pad}]"
    return str(expr)


def _fmt_parameter(param: ParameterDeclaration) -> str:
    """Format a parameter declaration, including any leading/trailing comments."""
    parts = [str(c) for c in param.leading_comments]
    has_default = param.default is not None and not isinstance(param.default, UndefinedLiteral)
    parts.append(f"{param.name}{'=' + str(param.default) if has_default else ''}")
    parts.extend(str(c) for c in param.trailing_comments)
    return " ".join(parts)


def _join_str_params(params) -> str:
    return ", ".join(_fmt_parameter(p) for p in params)


def _fmt_node(node: ASTNode, indent: int, w: int) -> str:
    """Format any top-level or block-body node."""
    pad = " " * indent

    if isinstance(node, BlankLine):
        return ""
    if isinstance(node, CommentLine):
        return f"{pad}//{node.text}"
    if isinstance(node, CommentSpan):
        return f"{pad}/*{node.text}*/"
    if isinstance(node, UseStatement):
        return f"{pad}use <{node.filepath.val}>"
    if isinstance(node, IncludeStatement):
        return f"{pad}include <{node.filepath.val}>"
    if isinstance(node, Assignment):
        rhs = _fmt_expr(node.expr, indent, w)
        inline = f"{pad}{node.name} = {rhs};"
        if rhs.startswith("[\n"):
            # Re-format so ] aligns with [: pass the column of [ as indent.
            bracket_col = indent + len(str(node.name)) + 3
            rhs = _fmt_expr(node.expr, bracket_col, w)
            return f"{pad}{node.name} = {rhs};"
        if len(inline.split("\n")[0]) > _MULTILINE_CHAR_LIMIT:
            rhs2 = _fmt_expr(node.expr, indent + w, w)
            return f"{pad}{node.name} =\n{' ' * (indent + w)}{rhs2};"
        return inline
    if isinstance(node, FunctionDeclaration):
        pre = " ".join(str(c) for c in node.pre_name_comments)
        post_n = " ".join(str(c) for c in node.post_name_comments)
        post_p = " ".join(str(c) for c in node.post_params_comments)
        head = f"{pad}function{' ' + pre if pre else ''} {node.name}{' ' + post_n if post_n else ''}"
        params_inline = _join_str_params(node.parameters)
        post_p_str = f" {post_p}" if post_p else ""
        expr_pad = " " * (indent + w)
        if len(f"{head}({params_inline}){post_p_str} =") > _MULTILINE_CHAR_LIMIT:
            param_block = _fmt_multiline_args(head, node.parameters, indent, w, fmt_fn=_fmt_parameter)
            return f"{param_block}{post_p_str} =\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
        return f"{head}({params_inline}){post_p_str} =\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
    if isinstance(node, ModuleDeclaration):
        pre = " ".join(str(c) for c in node.pre_name_comments)
        post_n = " ".join(str(c) for c in node.post_name_comments)
        post_p = " ".join(str(c) for c in node.post_params_comments)
        head = f"{pad}module{' ' + pre if pre else ''} {node.name}{' ' + post_n if post_n else ''}"
        params_inline = _join_str_params(node.parameters)
        post_p_str = f" {post_p}" if post_p else ""
        block = _fmt_block(node.children, indent, w)
        if len(f"{head}({params_inline}){post_p_str}") > _MULTILINE_CHAR_LIMIT:
            param_block = _fmt_multiline_args(head, node.parameters, indent, w, fmt_fn=_fmt_parameter)
            return f"{param_block}{post_p_str} {block}"
        return f"{head}({params_inline}){post_p_str} {block}"
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

    if isinstance(node, Assignment):
        return _fmt_node(node, indent, w)

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
        inner_pad = " " * (indent + w)
        formatted = [_fmt_assign(a, indent + w, w) for a in _as_list(node.assignments)]
        inline = f"{pad}{prefix}for ({', '.join(formatted)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            head = f"{pad}{prefix}for (\n{inner_pad}{assign_lines}\n{pad})"
        else:
            head = inline
        return head + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularIntersectionFor):
        inner_pad = " " * (indent + w)
        formatted = [_fmt_assign(a, indent + w, w) for a in _as_list(node.assignments)]
        inline = f"{pad}{prefix}intersection_for ({', '.join(formatted)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or any("\n" in fa for fa in formatted):
            assign_lines = (",\n" + inner_pad).join(formatted)
            head = f"{pad}{prefix}intersection_for (\n{inner_pad}{assign_lines}\n{pad})"
        else:
            head = inline
        return head + _fmt_child(node.body, indent, w)

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
        head = f"{pad}{prefix}echo"
        inline = f"{head}({_join_str(node.arguments)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT:
            call = _fmt_multiline_args(head, node.arguments, indent, w,
                                       fmt_fn=lambda a: _fmt_argument(a, indent + w, w))
        else:
            call = inline
        return call + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularAssert):
        head = f"{pad}{prefix}assert"
        inline = f"{head}({_join_str(node.arguments)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT:
            call = _fmt_multiline_args(head, node.arguments, indent, w,
                                       fmt_fn=lambda a: _fmt_argument(a, indent + w, w))
        else:
            call = inline
        return call + _fmt_child(node.children, indent, w)

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
