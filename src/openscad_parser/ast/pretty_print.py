"""Pretty-printer: convert an OpenSCAD AST back to formatted source code."""
from __future__ import annotations
import dataclasses
from .nodes import (
    _condition, _postfix_operand,
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
    RenderExpression,
    RangeLiteral,
    ListComprehension,
    VectorElement,
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
    parts = []
    prev_complex = False
    blanks = 0  # BlankLines seen since the last node printed
    for node in nodes:
        if _is_same_line_comment(node) and parts:
            parts[-1] += f"  {node}"
            continue
        if isinstance(node, BlankLine):
            blanks += 1
            continue
        # Two blank lines after a declaration, or the source's own if more.
        # Adding the two to the source's (which a re-parse keeps as
        # BlankLines) grew the gap by two on every reformat.
        if parts:
            parts.extend([""] * (max(blanks, 2) if prev_complex else blanks))
        blanks = 0
        parts.append(_fmt_node(node, 0, indent_width))
        prev_complex = isinstance(node, (ModuleDeclaration, FunctionDeclaration))
    return _coalesce_paren_bracket("\n".join(parts))


def _coalesce_paren_bracket(text: str) -> str:
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


def _as_list(val) -> list:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _join_str(items) -> str:
    return ", ".join(str(i) for i in items)


def _fmt_list_elem(elem, indent: int, w: int) -> str:
    pad = " " * indent
    inner_pad = " " * (indent + w)
    if isinstance(elem, CommentedExpr) and isinstance(elem.expr, VectorElement):
        lead = "".join(f"{c}\n{pad}" if isinstance(c, CommentLine) else f"{c} " for c in elem.leading_comments)
        return lead + _fmt_list_elem(elem.expr, indent, w) + _fmt_trailing_comments(elem.trailing_comments, pad)
    if isinstance(elem, ListCompFor):
        formatted, joined = _fmt_assigns(elem.assignments, indent + w, w, inner_pad)
        body = _fmt_list_elem(elem.body, indent + w, w)
        assigns_inline = ", ".join(formatted)
        if any("\n" in fa for fa in formatted) or len(f"for ({assigns_inline})") + indent > _MULTILINE_CHAR_LIMIT:
            assign_lines = joined
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
        formatted, joined = _fmt_assigns(elem.assignments, indent + w, w, inner_pad)
        body = _fmt_list_elem(elem.body, indent, w)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = joined
            return f"let(\n{inner_pad}{assign_lines}\n{pad})\n{pad}{body}"
        assigns = ", ".join(formatted)
        return f"let({assigns})\n{pad}{body}"
    if isinstance(elem, LetOp):
        formatted, joined = _fmt_assigns(elem.assignments, indent + w, w, inner_pad)
        body = _fmt_expr(elem.body, indent, w)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = joined
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
    return _fmt_expr(elem, indent, w)  # which indents what follows a comment


def _add_item_lines(lines: list, text: str, lead: list, trail: list, inner_pad: str) -> None:
    """Append one list item (argument, parameter, assignment, element),
    `text` already carrying its comma, with its `//` comments: the first one
    before it at the end of the previous line (after that item's comma), the
    first one after it at the end of its own, and any others on lines of
    their own -- joined onto one line, two comments became one."""
    if lead and len(lines) > 1:
        lines[-1] += f"  {lead[0]}"
        lead = lead[1:]
    lines.extend(f"{inner_pad}{c}" for c in lead)
    lines.append(f"{inner_pad}{text}" + (f"  {trail[0]}" if trail else ""))
    lines.extend(f"{inner_pad}{c}" for c in trail[1:])


def _strip_line_comments(expr):
    """(leading, trailing, expr) with the `//` comments taken off a
    CommentedExpr; anything else comes back with none."""
    if not isinstance(expr, CommentedExpr):
        return [], [], expr
    lead = [c for c in expr.leading_comments if isinstance(c, CommentLine)]
    trail = [c for c in expr.trailing_comments if isinstance(c, CommentLine)]
    if not lead and not trail:
        return [], [], expr
    rest_lead = [c for c in expr.leading_comments if not isinstance(c, CommentLine)]
    rest_trail = [c for c in expr.trailing_comments if not isinstance(c, CommentLine)]
    if not rest_lead and not rest_trail:
        return lead, trail, expr.expr
    return lead, trail, dataclasses.replace(expr, leading_comments=rest_lead, trailing_comments=rest_trail)


def _pop_line_comments(item):
    """(leading, trailing, item) with the `//` comments taken off an argument
    or parameter, wherever on it the comment attacher put them."""
    lead, trail, changes = [], [], {}
    fields = {PositionalArgument: ("expr",), NamedArgument: ("name", "expr"),
              ParameterDeclaration: ("name", "default"), Assignment: ("name", "expr")}.get(type(item), ())
    for name in fields:
        l, t, cleaned = _strip_line_comments(getattr(item, name))
        if l or t:
            lead += l
            trail += t
            changes[name] = cleaned
    if isinstance(item, ParameterDeclaration):
        for name, out in (("leading_comments", lead), ("trailing_comments", trail)):
            comments = getattr(item, name)
            if any(isinstance(c, CommentLine) for c in comments):
                out += [c for c in comments if isinstance(c, CommentLine)]
                changes[name] = [c for c in comments if not isinstance(c, CommentLine)]
    return lead, trail, (dataclasses.replace(item, **changes) if changes else item)


def _has_line_comment(node) -> bool:
    """Whether a `//` comment is attached anywhere in `node` (a node or a
    list of them). A line comment ends at the newline, so whatever holds one
    cannot be printed on a single line without commenting out the rest."""
    if isinstance(node, CommentLine):
        return True
    if isinstance(node, list):
        return any(_has_line_comment(n) for n in node)
    if isinstance(node, ASTNode):
        return any(_has_line_comment(getattr(node, f.name))
                   for f in dataclasses.fields(node) if f.name not in ("position", "scope"))
    return False


def _fmt_multiline_args(head: str, args: list, indent: int, w: int, fmt_fn=str) -> str:
    """One argument (or parameter) per line. A `//` comment before an item is
    moved to the end of the line before it -- the `(` line for the first --
    and one after it goes after its comma: printed where it was attached, it
    would sit alone on a line (and re-parse as a standalone comment) or
    swallow the comma. Same treatment as list elements get."""
    inner_pad = " " * (indent + w)
    pad = " " * indent
    lines = [f"{head}("]
    for i, arg in enumerate(args):
        lead, trail, arg = _pop_line_comments(arg)
        _add_item_lines(lines, f"{fmt_fn(arg)}{',' if i < len(args) - 1 else ''}", lead, trail, inner_pad)
    return "\n".join(lines) + f"\n{pad})"


def _fmt_assign(assign, indent: int, w: int) -> str:
    return f"{assign.name} = {_fmt_expr(assign.expr, indent, w)}"


def _fmt_assigns(assignments, indent: int, w: int, inner_pad: str) -> tuple[list[str], str]:
    """(formatted, joined) for a let/for assignment list: `formatted` for an
    inline join, `joined` one per line. A `//` comment before an assignment
    goes after the previous one's comma, as in argument lists; any comment
    puts a newline in `formatted`, which sends every caller multiline."""
    items = []
    for a in _as_list(assignments):
        lead, trail, a = _pop_line_comments(a)
        items.append([_fmt_assign(a, indent, w), lead, trail])
    lines = [""]  # stands for the opening line, which callers write themselves
    for i, (text, lead, trail) in enumerate(items):
        _add_item_lines(lines, text + ("," if i < len(items) - 1 else ""), lead, trail, inner_pad)
    has_comment = any(lead or trail for _, lead, trail in items)
    formatted = [t + ("\n" if has_comment else "") for t, _, _ in items]
    return formatted, "\n".join(lines[1:])[len(inner_pad):]


def _fmt_argument(arg, indent: int, w: int) -> str:
    if isinstance(arg, PositionalArgument):
        return _fmt_expr(arg.expr, indent, w)
    if isinstance(arg, NamedArgument):
        return f"{arg.name}={_fmt_expr(arg.expr, indent, w)}"
    return str(arg)


def _fmt_ternary_chain(expr: TernaryOp, indent: int, w: int) -> str:
    pad = " " * indent
    inner_pad = " " * (indent + w)
    parts = []
    node = expr
    comments: list = []  # on an else-branch that is itself a ternary
    while isinstance(node, TernaryOp):
        parts.append((node.condition, node.true_expr, comments))
        node = node.false_expr
        comments = []
        if isinstance(node, CommentedExpr) and isinstance(node.expr, TernaryOp):
            # Unwrapped to continue the chain -- its comments go before the
            # next condition, rather than being dropped with the wrapper.
            comments = node.leading_comments + node.trailing_comments
            node = node.expr
    final = node
    lines = []
    for i, (cond, true_expr, lead) in enumerate(parts):
        true_str = _fmt_expr(true_expr, indent + w, w)
        prefix = "" if i == 0 else f"{pad}: " + "".join(
            f"{c}\n{pad}  " if isinstance(c, CommentLine) else f"{c} " for c in lead)
        lines.append(f"{prefix}{_condition(cond)} ?\n{inner_pad}{true_str}")
    lines.append(f"{pad}: {_fmt_expr(final, indent + w, w)}")
    return "\n".join(lines)


def _fmt_trailing_comments(comments: list, pad: str) -> str:
    """Comments after an expression. After a `//` one the line must end, or
    it would comment out the `,` `)` or `;` its caller adds next."""
    out = "".join(f" {c}" for c in comments)
    return out + f"\n{pad}" if comments and isinstance(comments[-1], CommentLine) else out


def _fmt_expr(expr, indent: int, w: int) -> str:
    pad = " " * indent
    if isinstance(expr, CommentedExpr):
        if any(isinstance(c, CommentLine) for c in expr.leading_comments):
            inner_pad = " " * indent
            last_ll = max(i for i, c in enumerate(expr.leading_comments) if isinstance(c, CommentLine))
            line_part = expr.leading_comments[:last_ll + 1]
            inline_part = expr.leading_comments[last_ll + 1:]
            body_parts = [str(c) for c in inline_part]
            body_parts.append(_fmt_expr(expr.expr, indent, w))
            body = " ".join(body_parts) + _fmt_trailing_comments(expr.trailing_comments, pad)
            all_lines = [str(c) for c in line_part] + [body]
            return "\n".join([all_lines[0]] + [f"{inner_pad}{l}" for l in all_lines[1:]])
        parts = [str(c) for c in expr.leading_comments]
        parts.append(_fmt_expr(expr.expr, indent, w))
        return " ".join(parts) + _fmt_trailing_comments(expr.trailing_comments, pad)
    if isinstance(expr, TernaryOp):
        false_inner = expr.false_expr.expr if isinstance(expr.false_expr, CommentedExpr) else expr.false_expr
        if isinstance(false_inner, TernaryOp):
            return _fmt_ternary_chain(expr, indent, w)
        pad2 = " " * (indent + w)
        def _fmt_branch(branch):
            if isinstance(branch, TernaryOp):
                return _fmt_expr(branch, indent + w, w)
            return _fmt_expr(branch, indent + w + 2, w)
        return (
            f"{_condition(expr.condition)}\n"
            f"{pad2}? {_fmt_branch(expr.true_expr)}\n"
            f"{pad2}: {_fmt_branch(expr.false_expr)}"
        )
    if isinstance(expr, (AssertOp, EchoOp)):
        head = "assert" if isinstance(expr, AssertOp) else "echo"
        if _has_line_comment(expr.arguments):
            call = _fmt_multiline_args(head, expr.arguments, indent, w,
                                       fmt_fn=lambda a: _fmt_argument(a, indent + w, w))
        else:
            call = f"{head}({', '.join(str(a) for a in expr.arguments)})"
        if isinstance(expr.body, UndefinedLiteral):
            return call
        return f"{call}\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, LetOp):
        inner_pad = " " * (indent + w)
        formatted, joined = _fmt_assigns(expr.assignments, indent + w, w, inner_pad)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = joined
            return (
                f"let(\n{inner_pad}{assign_lines}\n{pad})\n"
                f"{pad}{_fmt_expr(expr.body, indent, w)}"
            )
        assigns = ", ".join(formatted)
        return f"let({assigns})\n{pad}{_fmt_expr(expr.body, indent, w)}"
    if isinstance(expr, RangeLiteral) and _has_line_comment(expr):
        # A `//` comment runs to the end of the line, so each one goes after
        # the separator it followed, then a line break: `[0 :  // why` + `2]`.
        inner_pad = " " * (indent + w)
        parts = [expr.start] + ([] if expr.implicit_step else [expr.step]) + [expr.end]
        out, pending = "[", []
        for i, part in enumerate(parts):
            lead, trail, part = _strip_line_comments(part)
            pending += lead
            if pending:
                out += "  " + "  ".join(str(c) for c in pending) + "\n" + inner_pad
            elif i:
                out += " "
            out += _fmt_expr(part, indent + w, w) + (" :" if i < len(parts) - 1 else "")
            pending = trail
        if pending:
            out += "  " + "  ".join(str(c) for c in pending) + "\n" + " " * indent
        return out + "]"
    if isinstance(expr, RenderExpression):
        # Always braced: `x = render() cube(1);` does not parse. _fmt_block's
        # statements bring their own terminators.
        return f"render({_join_str(expr.arguments)}) {_fmt_block(expr.children, indent, w)}"
    if isinstance(expr, PrimaryCall):
        inline = str(expr)
        if len(inline) + indent > _MULTILINE_CHAR_LIMIT or _has_line_comment(expr.arguments):
            return _fmt_multiline_args(
                _postfix_operand(expr.left), expr.arguments, indent, w,
                fmt_fn=lambda a: _fmt_argument(a, indent + w, w),
            )
    if hasattr(expr, 'left') and hasattr(expr, 'right'):
        left_fmt = _fmt_expr(expr.left, indent, w)
        if left_fmt.startswith("[\n"):
            op = _BINARY_OP_SYMBOLS.get(type(expr).__name__)
            if op is not None:
                right_fmt = _fmt_expr(expr.right, indent, w)
                return f"{left_fmt} {op} {right_fmt}"
    if isinstance(expr, ListComprehension):
        inner_pad = " " * (indent + w)
        # `//` comments come off each element: one before it goes at the end
        # of the previous line, one after it after its comma.
        splits = [_strip_line_comments(e) for e in expr.elements]
        has_line_comment = any(lead or trail for lead, trail, _ in splits)
        formatted = [_fmt_list_elem(cleaned, indent + w, w) for _, _, cleaned in splits]
        any_multiline = has_line_comment or any("\n" in fe for fe in formatted)
        if not any_multiline:
            inline = f"[{', '.join(formatted)}]"
            if len(inline) + indent <= _MULTILINE_CHAR_LIMIT:
                return inline
        lines = ["["]
        for i, ((lcs, trail, _), elem_str) in enumerate(zip(splits, formatted)):
            comma = "" if i == len(expr.elements) - 1 else ","
            _add_item_lines(lines, f"{elem_str}{comma}", lcs, trail, inner_pad)
        return "\n".join(lines) + f"\n{pad}]"
    return str(expr)


def _fmt_parameter(param: ParameterDeclaration) -> str:
    parts = [str(c) for c in param.leading_comments]
    has_default = param.default is not None and not isinstance(param.default, UndefinedLiteral)
    parts.append(f"{param.name}{'=' + str(param.default) if has_default else ''}")
    parts.extend(str(c) for c in param.trailing_comments)
    return " ".join(parts)


def _join_str_params(params) -> str:
    return ", ".join(_fmt_parameter(p) for p in params)


def _fmt_node(node: ASTNode, indent: int, w: int) -> str:
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
            rhs = _fmt_expr(node.expr, indent + w, w)
            return f"{pad}{node.name} = {rhs};"
        if len(inline.split("\n")[0]) > _MULTILINE_CHAR_LIMIT:
            rhs2 = _fmt_expr(node.expr, indent + w, w)
            return f"{pad}{node.name} =\n{' ' * (indent + w)}{rhs2};"
        return inline
    if isinstance(node, FunctionDeclaration):
        head = _decl_head(pad, "function", node)
        params_inline = _join_str_params(node.parameters)
        post_p_str = _comments_after(node.post_params_comments, pad) + " ="
        expr_pad = " " * (indent + w)
        if len(f"{head}({params_inline}){post_p_str}") > _MULTILINE_CHAR_LIMIT or _has_line_comment(node.parameters):
            param_block = _fmt_multiline_args(head, node.parameters, indent, w, fmt_fn=_fmt_parameter)
            return f"{param_block}{post_p_str}\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
        return f"{head}({params_inline}){post_p_str}\n{expr_pad}{_fmt_expr(node.expr, indent + w, w)};"
    if isinstance(node, ModuleDeclaration):
        head = _decl_head(pad, "module", node)
        params_inline = _join_str_params(node.parameters)
        post_p_str = _comments_after(node.post_params_comments, pad) + " "
        block = _fmt_block(node.children, indent, w)
        if len(f"{head}({params_inline}){post_p_str}") > _MULTILINE_CHAR_LIMIT or _has_line_comment(node.parameters):
            param_block = _fmt_multiline_args(head, node.parameters, indent, w, fmt_fn=_fmt_parameter)
            return f"{param_block}{post_p_str}{block}"
        return f"{head}({params_inline}){post_p_str}{block}"
    if isinstance(node, ModuleInstantiation):
        return _fmt_inst(node, indent, w)
    return f"{pad}{node}"


def _comments_after(comments, pad: str) -> str:
    """Comments that follow something on its line, each after a space. A
    `//` one ends the line, so what came after it goes on the next line, at
    `pad`, rather than into the comment: `module m // why(a)` would parse as
    a module with no parameter list."""
    out = ""
    for c in comments:
        out += f" {c}"
        if isinstance(c, CommentLine):
            out += f"\n{pad}"
    return out.replace(f"\n{pad} ", f"\n{pad}")


def _decl_head(pad: str, keyword: str, node) -> str:
    """`module name` / `function name`, with the comments written around the
    name, ready for the `(` of the parameter list."""
    head = f"{pad}{keyword}{_comments_after(node.pre_name_comments, pad)}"
    head += ("" if head.endswith("\n" + pad) else " ") + str(node.name)
    return head + _comments_after(node.post_name_comments, pad)


def _is_same_line_comment(node) -> bool:
    # openscad_parser's grammar keeps no same_line flag; lalr's comment placer sets it.
    return isinstance(node, CommentLine) and getattr(node, "same_line", False)


def _split_opening_comment(nodes: list) -> tuple[str, list]:
    """A same-line comment first in a block ended its `{` line."""
    if nodes and _is_same_line_comment(nodes[0]):
        return f"  {nodes[0]}", nodes[1:]
    return "", nodes


def _fmt_statements(nodes: list, fmt) -> str:
    """Statements one per line, with a comment that ended a statement's line
    in the source put back at the end of that statement's (last) line."""
    lines = []
    for n in nodes:
        if _is_same_line_comment(n) and lines:
            lines[-1] += f"  {n}"
        else:
            lines.append(fmt(n))
    return "\n".join(lines)


def _fmt_block(nodes: list, indent: int, w: int) -> str:
    pad = " " * indent
    if not nodes:
        return "{}"
    head, nodes = _split_opening_comment(nodes)
    inner = _fmt_statements(nodes, lambda n: _fmt_node(n, indent + w, w))
    return "{" + head + "\n" + inner + "\n" + pad + "}"


def _ends_in_open_if(node) -> bool:
    """Whether an unbraced `node` ends in an `if` with no `else` -- which an
    `else` printed after it would bind to instead (the dangling else)."""
    while True:
        if isinstance(node, ModularIf):
            return True
        if isinstance(node, (ModularModifierShowOnly, ModularModifierHighlight,
                             ModularModifierBackground, ModularModifierDisable)):
            node = node.child
            continue
        tail = next((getattr(node, f) for f in ("false_branch", "children", "body")
                     if isinstance(getattr(node, f, None), list)), None)
        if not tail or len(tail) != 1:  # none, or braced when printed
            return False
        node = tail[0]


def _fmt_child(body, indent: int, w: int, brace_open_if: bool = False) -> str:
    nodes = _as_list(body)
    pad = " " * indent

    if not nodes:
        return ";"
    if len(nodes) == 1 and not (brace_open_if and _ends_in_open_if(nodes[0])):
        return "\n" + _fmt_inst(nodes[0], indent + w, w)
    head, nodes = _split_opening_comment(nodes)
    inner = _fmt_statements(nodes, lambda n: _fmt_inst(n, indent + w, w))
    return " {" + head + "\n" + inner + "\n" + pad + "}"


def _fmt_inst(node: ModuleInstantiation, indent: int, w: int, prefix: str = "") -> str:
    pad = " " * indent

    if isinstance(node, (CommentLine, CommentSpan, BlankLine)):  # placed in a nested block
        return _fmt_node(node, indent, w)

    if isinstance(node, Assignment):
        return _fmt_node(node, indent, w)

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
        if len(inline) > _MULTILINE_CHAR_LIMIT or _has_line_comment(node.arguments):
            call = _fmt_multiline_args(
                head, node.arguments, indent, w,
                fmt_fn=lambda a: _fmt_argument(a, indent + w, w),
            )
        else:
            call = inline
        return call + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularFor):
        inner_pad = " " * (indent + w)
        formatted, joined = _fmt_assigns(_as_list(node.assignments), indent + w, w, inner_pad)
        inline = f"{pad}{prefix}for ({', '.join(formatted)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or any("\n" in fa for fa in formatted):
            assign_lines = joined
            head = f"{pad}{prefix}for (\n{inner_pad}{assign_lines}\n{pad})"
        else:
            head = inline
        return head + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularIntersectionFor):
        inner_pad = " " * (indent + w)
        formatted, joined = _fmt_assigns(_as_list(node.assignments), indent + w, w, inner_pad)
        inline = f"{pad}{prefix}intersection_for ({', '.join(formatted)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or any("\n" in fa for fa in formatted):
            assign_lines = joined
            head = f"{pad}{prefix}intersection_for (\n{inner_pad}{assign_lines}\n{pad})"
        else:
            head = inline
        return head + _fmt_child(node.body, indent, w)

    if isinstance(node, ModularLet):
        inner_pad = " " * (indent + w)
        formatted, joined = _fmt_assigns(_as_list(node.assignments), indent + w, w, inner_pad)
        if len(formatted) > 1 or any("\n" in fa for fa in formatted):
            assign_lines = joined
            tail = _fmt_child(node.children, indent, w)
            return f"{pad}{prefix}let (\n{inner_pad}{assign_lines}\n{pad}){tail}"
        assigns = ", ".join(formatted)
        return f"{pad}{prefix}let ({assigns})" + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularEcho):
        head = f"{pad}{prefix}echo"
        inline = f"{head}({_join_str(node.arguments)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or _has_line_comment(node.arguments):
            call = _fmt_multiline_args(head, node.arguments, indent, w,
                                       fmt_fn=lambda a: _fmt_argument(a, indent + w, w))
        else:
            call = inline
        return call + _fmt_child(node.children, indent, w)

    if isinstance(node, ModularAssert):
        head = f"{pad}{prefix}assert"
        inline = f"{head}({_join_str(node.arguments)})"
        if len(inline) > _MULTILINE_CHAR_LIMIT or _has_line_comment(node.arguments):
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
        true_tail = _fmt_child(node.true_branch, indent, w, brace_open_if=True)
        false_tail = _fmt_child(node.false_branch, indent, w)
        connector = " else" if true_tail.startswith(" {") else f"\n{pad}else"
        return header + true_tail + connector + false_tail

    return f"{pad}{prefix}{node};"
