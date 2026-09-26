"""Comments for include_comments=True, attached after the parse.

The source is parsed with comments as whitespace -- the grammar every file
already parses under -- and each comment is then placed by position: between
statements into the statement list, inside an expression as a CommentedExpr,
around a declaration's name and parameters into its comment fields.

This replaced a grammar that allowed a comment only at the points it listed,
so a comment anywhere else -- in a ternary, after a `(`, inside `each if` --
was a syntax error: 19 of BOSL2's 57 files failed to parse with comments
kept. Ported from openscad_lalr_parser, which keeps every one of BOSL2's
comments this way.
"""
from __future__ import annotations

import bisect
import dataclasses
import re

from .builder import Position, _insert_blank_lines
from .nodes import (
    ASTNode, BlankLine, CommentLine, CommentSpan, CommentedExpr, Expression, FunctionDeclaration,
    Identifier, ModuleDeclaration, ModuleInstantiation, ParameterDeclaration, VectorElement,
)


# --- Comment extraction for include_comments mode ---

_COMMENT_RE = re.compile(
    r'//([^\n]*)'           # single-line comment
    r'|/\*([\s\S]*?)\*/'    # multi-line comment
    r'|"(?:[^"\\]|\\[\s\S])*"'  # string literal (skip); a backslash may escape a newline
)


def _line_of(newlines: list[int], offset: int) -> int:
    """1-based line of `offset`, given the offsets of every newline."""
    return bisect.bisect_left(newlines, offset) + 1


def _extract_comments(code: str, origin: str) -> list[ASTNode]:
    """Extract all comments from source code as AST nodes."""
    newlines = [m.start() for m in re.finditer("\n", code)]
    comments = []
    for m in _COMMENT_RE.finditer(code):
        kind = CommentLine if m.group(1) is not None else CommentSpan if m.group(2) is not None else None
        if kind is None:
            continue  # a string literal
        start = m.start()
        line = _line_of(newlines, start)
        col = start - newlines[line - 2] if line > 1 else start + 1
        pos = Position(origin=origin, line=line, column=col, start_offset=start, end_offset=m.end())
        comments.append(kind(position=pos, text=m.group(1) if kind is CommentLine else m.group(2)))
    return comments


def _is_inline_comment(comment: ASTNode, code: str) -> bool:
    """Return True if the comment shares a source line with non-comment code."""
    start = comment.position.start_offset
    end = comment.position.end_offset
    line_start = code.rfind('\n', 0, start)
    line_start = 0 if line_start < 0 else line_start + 1
    before = code[line_start:start].strip()
    if before:
        return True
    if isinstance(comment, CommentSpan):
        last_line_end = code.find('\n', end)
        if last_line_end < 0:
            last_line_end = len(code)
        after = code[end:last_line_end].strip()
        if after and not after.startswith('//') and not after.startswith('/*'):
            return True
    return False


def _classify_comments(comments: list[ASTNode], code: str) -> tuple[list[ASTNode], list[ASTNode]]:
    """Split comments into (inline, standalone) lists."""
    inline = []
    standalone = []
    for c in comments:
        if _is_inline_comment(c, code):
            inline.append(c)
        else:
            standalone.append(c)
    return inline, standalone


_SKIP_FIELDS = frozenset(('position', 'scope', 'leading_comments', 'trailing_comments',
                           'pre_name_comments', 'post_name_comments', 'post_params_comments'))


_STATEMENT_LIST_FIELDS = ("children", "body", "true_branch", "false_branch")
_STATEMENT_TYPES = (ModuleInstantiation, ModuleDeclaration, FunctionDeclaration)
# What an inline comment can wrap: expressions, and list-comprehension
# elements (`each`, `if`, `for` ...), which aren't Expressions -- with only
# those between them, a comment had nothing to attach to and was dropped.
_ATTACHABLE = (Expression, VectorElement)


def _blank_comments(code: str, comments: list) -> str:
    """`code` with every comment replaced by spaces (newlines kept), so
    looking back past comments for the previous real character is easy."""
    chars = list(code)
    for c in comments:
        for i in range(c.position.start_offset, c.position.end_offset):
            if chars[i] != "\n":
                chars[i] = " "
    return "".join(chars)


def _place_comment(stmts: list, comment, blanked: str, same_line: bool, top: bool = False) -> str:
    """Put `comment` into the statement list where it falls between
    statements, descending into nested blocks. Returns "placed", "head"
    (inside a statement's non-block part -- arguments, a condition -- where
    expression attachment takes it) or "top" (an own-line comment between
    top-level statements, which _inject_comments places with its blank
    lines)."""
    cs = comment.position.start_offset
    for node in stmts:
        if isinstance(node, (CommentLine, CommentSpan, BlankLine)):
            continue
        pos = node.position
        if pos.start_offset <= cs < pos.end_offset:
            return _place_in_statement(node, comment, blanked, same_line)
    if top and not same_line:
        return "top"
    index = sum(1 for n in stmts if n.position.start_offset < cs)  # comments come in source order
    if index == 0 and top:
        return "head"
    if isinstance(comment, CommentLine):
        comment.same_line = same_line
    stmts.insert(index, comment)
    return "placed"


def _place_in_statement(node, comment, blanked: str, same_line: bool) -> str:
    child = getattr(node, "child", None)  # the #/%/!/* modifiers wrap one statement
    if isinstance(child, ASTNode):
        return _place_in_statement(child, comment, blanked, same_line)
    # The block the comment is in: the last one starting before it (an if/else
    # has two). Failing that, the next block if only its `{` comes between
    # (`module m() { // why`, or an own-line comment atop the block).
    cs = comment.position.start_offset
    block = next_block = None
    for name in _STATEMENT_LIST_FIELDS:
        stmts = getattr(node, name, None)
        if not isinstance(stmts, list):
            continue
        # By its first STATEMENT: a comment placed there already may come first.
        first = next((n for n in stmts if isinstance(n, ASTNode)
                      and not isinstance(n, (CommentLine, CommentSpan, BlankLine))), None)
        if first is None:
            continue
        if first.position.start_offset <= cs:
            block = stmts
        elif next_block is None:
            next_block = stmts
    inside_block = block is not None and any(
        n.position.start_offset <= cs < n.position.end_offset
        for n in block if not isinstance(n, (CommentLine, CommentSpan, BlankLine)))
    if not inside_block and next_block is not None and blanked[:cs].rstrip().endswith("{"):
        block = next_block  # atop a block: an else's, even with the if's block before it
    if block is None:
        return "head"
    return _place_comment(block, comment, blanked, same_line)


def _attach_inline_comments(ast_nodes: list[ASTNode], inline_comments: list[ASTNode]) -> list[ASTNode]:
    """Returns the comments it found no place for, for the caller to keep as
    top-level ones: dropping them lost the text."""
    """Walk AST and wrap expressions adjacent to inline comments in CommentedExpr."""
    if not inline_comments:
        return []
    inline_comments.sort(key=lambda c: c.position.start_offset)
    used: set[int] = set()
    for node in ast_nodes:
        _walk_attach(node, inline_comments, used)

    # Attach remaining unused inline comments as trailing on the nearest
    # preceding top-level node's last expression field.
    for ci, comment in enumerate(inline_comments):
        if ci in used:
            continue
        cs = comment.position.start_offset
        best_node = None
        for node in ast_nodes:
            if isinstance(node, (CommentLine, CommentSpan, BlankLine)):
                continue
            if node.position.end_offset <= cs:
                best_node = node
        if best_node is not None:
            _attach_trailing_to_last_expr(best_node, comment)
            used.add(ci)

    return [c for ci, c in enumerate(inline_comments) if ci not in used]


def _attach_trailing_to_last_expr(node: ASTNode, comment: ASTNode):
    """Attach a trailing comment to the last Expression field in node."""
    last_expr_info = None
    for f in dataclasses.fields(node):
        if f.name in _SKIP_FIELDS:
            continue
        val = getattr(node, f.name)
        if isinstance(val, Expression):
            last_expr_info = (node, f.name, None, val)
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                if isinstance(item, Expression):
                    last_expr_info = (node, f.name, idx, item)
                elif isinstance(item, ASTNode):
                    for cf in dataclasses.fields(item):
                        if cf.name in _SKIP_FIELDS:
                            continue
                        cval = getattr(item, cf.name)
                        if isinstance(cval, Expression):
                            last_expr_info = (item, cf.name, None, cval)
    if last_expr_info is None:
        return
    owner, fname, lidx, expr = last_expr_info
    if isinstance(expr, CommentedExpr):
        expr.trailing_comments.append(comment)
    else:
        wrapped = CommentedExpr(
            position=expr.position,
            leading_comments=[],
            trailing_comments=[comment],
            expr=expr,
        )
        if lidx is None:
            setattr(owner, fname, wrapped)
        else:
            getattr(owner, fname)[lidx] = wrapped


def _walk_attach(node: ASTNode, comments: list[ASTNode], used: set[int]):
    """Recursively attach inline comments to Expression fields of node."""
    if not isinstance(node, ASTNode) or isinstance(node, (CommentedExpr, CommentLine, CommentSpan)):
        return

    ns = node.position.start_offset
    ne = node.position.end_offset

    has_relevant = any(
        i not in used and ns <= comments[i].position.start_offset < ne
        for i in range(len(comments))
    )
    if not has_relevant:
        for f in dataclasses.fields(node):
            if f.name in _SKIP_FIELDS:
                continue
            val = getattr(node, f.name)
            if isinstance(val, ASTNode):
                _walk_attach(val, comments, used)
            elif isinstance(val, list):
                for item in val:
                    if isinstance(item, ASTNode):
                        _walk_attach(item, comments, used)
        return

    # Collect wrappable Expression fields, including from non-Expression
    # containers like PositionalArgument, NamedArgument, ParameterDeclaration.
    # Each entry: (owner_node, field_name, list_index_or_None, expr)
    expr_fields = []
    non_expr_children = []

    for f in dataclasses.fields(node):
        if f.name in _SKIP_FIELDS:
            continue
        if f.name == "step" and getattr(node, "implicit_step", False):
            continue  # synthesized for [a:b]; it spans the whole range and would swallow its comments
        val = getattr(node, f.name)
        if isinstance(val, _ATTACHABLE) and not isinstance(val, CommentedExpr):
            expr_fields.append((node, f.name, None, val))
        elif isinstance(val, ASTNode):
            non_expr_children.append(val)
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                if isinstance(item, _ATTACHABLE) and not isinstance(item, CommentedExpr):
                    expr_fields.append((node, f.name, idx, item))
                elif isinstance(item, _STATEMENT_TYPES) or (f.name in _STATEMENT_LIST_FIELDS and isinstance(item, ASTNode)):
                    # A child statement (an assignment in a block too): its
                    # own walk attaches its comments. Mined here, its NAME
                    # became one of this node's expressions, and a comment in
                    # this node's arguments landed on it (`translate([1, // c`
                    # ... `cube // c(1);`, or a last parameter's comment on
                    # the body's first assignment).
                    non_expr_children.append(item)
                elif isinstance(item, ASTNode):
                    _collect_container_exprs(item, expr_fields, non_expr_children)

    expr_fields.sort(key=lambda x: x[3].position.start_offset)

    leading_map: dict[int, list] = {ei: [] for ei in range(len(expr_fields))}
    trailing_map: dict[int, list] = {ei: [] for ei in range(len(expr_fields))}

    child_spans = [(c.position.start_offset, c.position.end_offset) for c in non_expr_children]
    for ci, comment in enumerate(comments):
        if ci in used:
            continue
        cs = comment.position.start_offset
        if cs < ns or cs >= ne:
            continue
        if any(s <= cs < e for s, e in child_spans):
            continue  # inside a child statement: its own walk places it

        attached = False
        for ei, (owner, fname, lidx, expr) in enumerate(expr_fields):
            es = expr.position.start_offset
            if cs < es:
                leading_map[ei].append((ci, comment))
                used.add(ci)
                attached = True
                break
            elif cs >= expr.position.end_offset:
                continue
            # Inside this expression: the recursion below attaches it within.
            # Falling through made it the NEXT expression's leading comment.
            attached = True
            break
        if not attached and expr_fields:
            last_ei = len(expr_fields) - 1
            if cs >= expr_fields[last_ei][3].position.end_offset:
                trailing_map[last_ei].append((ci, comment))
                used.add(ci)

    for ei, (owner, fname, lidx, expr) in enumerate(expr_fields):
        leading = [c for _, c in leading_map[ei]]
        trailing = [c for _, c in trailing_map[ei]]

        if leading or trailing:
            wrapped = CommentedExpr(
                position=expr.position,
                leading_comments=leading,
                trailing_comments=trailing,
                expr=expr,
            )
            if lidx is None:
                setattr(owner, fname, wrapped)
            else:
                getattr(owner, fname)[lidx] = wrapped

        _walk_attach(expr, comments, used)

    for child in non_expr_children:
        _walk_attach(child, comments, used)


def _collect_container_exprs(container: ASTNode, expr_fields: list, non_expr_children: list):
    """Extract Expression fields from a non-Expression container node."""
    found_expr = False
    for f in dataclasses.fields(container):
        if f.name in _SKIP_FIELDS:
            continue
        val = getattr(container, f.name)
        if isinstance(val, Expression) and not isinstance(val, CommentedExpr):
            expr_fields.append((container, f.name, None, val))
            found_expr = True
        elif isinstance(val, list):
            for idx, item in enumerate(val):
                if isinstance(item, Expression) and not isinstance(item, CommentedExpr):
                    expr_fields.append((container, f.name, idx, item))
                    found_expr = True
    if not found_expr:
        non_expr_children.append(container)


def _find_char_skipping_comments(code: str, frm: int, ch: str, comments: list[ASTNode]) -> int:
    """Scan raw source from `frm` for the next occurrence of `ch`, skipping
    over any already-extracted comment span encountered along the way (so a
    stray '(' or ')' inside a comment's own text is never mistaken for the
    real token). Returns -1 if not found.

    Needed because the grammar captures no location for the parameter
    list's own '(' / ')' tokens -- only NAME and the whole declaration's
    span are available (see transformer.py's
    function_definition/module_definition/parameter_with_default).
    """
    i = frm
    n = len(code)
    while i < n:
        skipped = False
        for c in comments:
            if c is not None and c.position.start_offset == i:
                i = c.position.end_offset
                skipped = True
                break
        if skipped:
            continue
        if code[i] == ch:
            return i
        i += 1
    return -1


def _claim_comment_spans_in_range(lo: int, hi: int, out: list, comments: list) -> None:
    """Moves every CommentSpan in `comments` whose start offset falls in
    [lo, hi) into `out`, nulling its slot in `comments` in place so a later
    pass (the inline/standalone split) never sees it again."""
    if lo >= hi:
        return
    for idx, c in enumerate(comments):
        if c is None or not isinstance(c, CommentSpan):
            continue
        cs = c.position.start_offset
        if lo <= cs < hi:
            out.append(c)
            comments[idx] = None


def _claim_decl_signature_comments(decl: ASTNode, name: Identifier, parameters: list[ParameterDeclaration],
                                    body_start: int, pre_name: list, post_name: list, post_params: list,
                                    code: str, comments: list) -> None:
    """Claims '/* */' comments (CommentSpan only -- these fields' own
    declared type) in every structural gap a FunctionDeclaration/
    ModuleDeclaration doesn't expose as any Expression field: before the
    name, between the name and the parameter list, between adjacent
    parameters (including a parameter with no default value, which
    _walk_attach's own generic Expression-field scan never visits at all,
    since it only descends into fields whose value IS an Expression),
    between the last parameter and ')', and between ')' and the body.

    ponytail: when there are zero parameters, the "between name and '('"
    and "between '(' and ')'" gaps are both real but there's no parameter
    to own the latter -- folded into post_params_comments rather than
    adding a dedicated field neither language's AST declares.
    """
    name_start = name.position.start_offset
    name_end = name.position.end_offset
    _claim_comment_spans_in_range(decl.position.start_offset, name_start, pre_name, comments)

    open_paren = _find_char_skipping_comments(code, name_end, '(', comments)
    paren_open_pos = open_paren if open_paren >= 0 else name_end
    _claim_comment_spans_in_range(name_end, paren_open_pos, post_name, comments)
    cursor = open_paren + 1 if open_paren >= 0 else name_end

    for p in parameters:
        _claim_comment_spans_in_range(cursor, p.position.start_offset, p.leading_comments, comments)
        cursor = p.position.end_offset

    close_paren = _find_char_skipping_comments(code, cursor, ')', comments)
    paren_close_pos = close_paren if close_paren >= 0 else cursor
    if parameters:
        _claim_comment_spans_in_range(cursor, paren_close_pos, parameters[-1].trailing_comments, comments)
    else:
        _claim_comment_spans_in_range(cursor, paren_close_pos, post_params, comments)
    cursor = close_paren + 1 if close_paren >= 0 else cursor
    _claim_comment_spans_in_range(cursor, body_start, post_params, comments)


def _walk_attach_decl_comments(node: ASTNode, code: str, comments: list) -> None:
    """Recurses through `node` looking for FunctionDeclaration/
    ModuleDeclaration nodes (which can nest inside a module's own
    children), claiming their signature-gap comments. A generic
    reflection-based walk over dataclass fields (mirrors _walk_attach's own
    field introspection), since -- unlike the C++ port, which needs an
    explicit per-NodeKind switch -- Python's dataclasses.fields() already
    gives a free generic tree walk.
    """
    if not isinstance(node, ASTNode) or isinstance(node, (CommentedExpr, CommentLine, CommentSpan)):
        return

    if isinstance(node, FunctionDeclaration):
        _claim_decl_signature_comments(node, node.name, node.parameters, node.expr.position.start_offset,
                                        node.pre_name_comments, node.post_name_comments, node.post_params_comments,
                                        code, comments)
    elif isinstance(node, ModuleDeclaration):
        body_start = node.children[0].position.start_offset if node.children else node.position.end_offset
        _claim_decl_signature_comments(node, node.name, node.parameters, body_start, node.pre_name_comments,
                                        node.post_name_comments, node.post_params_comments, code, comments)

    for f in dataclasses.fields(node):
        if f.name in _SKIP_FIELDS:
            continue
        val = getattr(node, f.name)
        if isinstance(val, ASTNode):
            _walk_attach_decl_comments(val, code, comments)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, ASTNode):
                    _walk_attach_decl_comments(item, code, comments)


def _attach_declaration_comments(ast_nodes: list[ASTNode], code: str, comments: list) -> None:
    """Claims declaration-signature comments across the whole AST. Must run
    BEFORE _classify_comments/_attach_inline_comments -- a '/* */' comment
    alone on its own line before a parameter is classified *standalone* by
    _is_inline_comment, which this pass still needs to claim, so it operates
    on the full extracted comment list, not just the inline subset.
    """
    for node in ast_nodes:
        _walk_attach_decl_comments(node, code, comments)


def _attach_all_comments(ast: list[ASTNode], code: str, origin: str) -> list[ASTNode]:
    """Shared by getASTfromString/_parse_single_file: extracts comments,
    claims declaration-signature comments first (see
    _attach_declaration_comments), then runs the existing inline/standalone
    pipeline over whatever's left.
    """
    comments = _extract_comments(code, origin)
    blanked = _blank_comments(code, comments)
    _attach_declaration_comments(ast, code, comments)
    comments = [c for c in comments if c is not None]
    inline, standalone = _classify_comments(comments, code)
    # Comments that sit between statements belong in the statement list, at
    # any depth: a `//` ending a statement's line after that statement (it
    # was wrapped round the statement's last expression and printed before
    # the `;`, or after a child module's NAME), an own-line one where it is
    # (it was moved out to top level, after the whole statement). Inside a
    # statement's arguments or condition, expression attachment takes it.
    expr_comments, top_level = [], []
    for c in inline:
        if not (isinstance(c, CommentLine) and _place_comment(ast, c, blanked, True, top=True) == "placed"):
            expr_comments.append(c)
    for c in standalone:
        where = _place_comment(ast, c, blanked, False, top=True)
        if where == "top":
            top_level.append(c)
        elif where == "head":
            expr_comments.append(c)
    top_level += _attach_inline_comments(ast, expr_comments)
    top_level.sort(key=lambda c: c.position.start_offset)
    for node in ast:
        _blank_lines_in_blocks(node)
    return _inject_comments(ast, top_level, code, origin)


def _blank_lines_in_blocks(node) -> None:
    """A blank line between two `//` comments in a block, as the grammar-based
    comment parse kept it (_insert_blank_lines); top-level ones are
    _inject_comments' job."""
    if not isinstance(node, ASTNode) or isinstance(node, (CommentedExpr, CommentLine, CommentSpan, BlankLine)):
        return
    for f in dataclasses.fields(node):
        if f.name in _SKIP_FIELDS:
            continue
        val = getattr(node, f.name)
        if isinstance(val, list):
            if f.name in _STATEMENT_LIST_FIELDS:
                val = _insert_blank_lines(val)
                setattr(node, f.name, val)
            for item in val:
                _blank_lines_in_blocks(item)
        elif isinstance(val, ASTNode):
            _blank_lines_in_blocks(val)


def _inject_comments(ast_nodes: list[ASTNode], comments: list[ASTNode], code: str, origin: str) -> list[ASTNode]:
    """Merge standalone comment nodes into top-level AST node list."""
    if not comments:
        return ast_nodes

    result = []
    comment_idx = 0
    prev_end_line = 0
    lines = code.split('\n')
    newlines = [m.start() for m in re.finditer("\n", code)]

    for node in ast_nodes:
        node_line = node.position.line if hasattr(node, 'position') and node.position else float('inf')

        while comment_idx < len(comments) and comments[comment_idx].position.line < node_line:
            comment = comments[comment_idx]
            cl = comment.position.line
            if prev_end_line > 0 and cl - prev_end_line > 1:
                # One BlankLine for the gap, however many blank lines it held.
                for gap_line in range(prev_end_line + 1, cl):
                    line_content = lines[gap_line - 1] if gap_line <= len(lines) else ''
                    if line_content.strip() == '':
                        result.append(BlankLine(position=Position(
                            origin=origin, line=gap_line, column=1)))
                        break
            result.append(comment)
            if isinstance(comment, CommentLine):
                prev_end_line = comment.position.line
            else:
                prev_end_line = comment.position.line + comment.text.count('\n')
            comment_idx += 1

        result.append(node)
        node_end = node.position.line
        if hasattr(node, 'position') and node.position and node.position.end_offset > 0:
            node_end = _line_of(newlines, node.position.end_offset)
        prev_end_line = max(prev_end_line, node_end)

    while comment_idx < len(comments):
        comment = comments[comment_idx]
        result.append(comment)
        comment_idx += 1

    return result
