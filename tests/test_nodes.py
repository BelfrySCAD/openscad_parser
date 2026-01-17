"""Tests for AST node string representations."""

from openscad_parser.ast.builder import Position
from openscad_parser.ast.nodes import (
    CommentLine,
    CommentSpan,
    Identifier,
    StringLiteral,
    NumberLiteral,
    BooleanLiteral,
    UndefinedLiteral,
    ParameterDeclaration,
    PositionalArgument,
    NamedArgument,
    RangeLiteral,
    Assignment,
    LetOp,
    EchoOp,
    AssertOp,
    UnaryMinusOp,
    AdditionOp,
    SubtractionOp,
    MultiplicationOp,
    DivisionOp,
    ModuloOp,
    ExponentOp,
    BitwiseAndOp,
    BitwiseOrOp,
    BitwiseNotOp,
    BitwiseShiftLeftOp,
    BitwiseShiftRightOp,
    LogicalAndOp,
    LogicalOrOp,
    LogicalNotOp,
    TernaryOp,
    EqualityOp,
    InequalityOp,
    GreaterThanOp,
    GreaterThanOrEqualOp,
    LessThanOp,
    LessThanOrEqualOp,
    FunctionLiteral,
    PrimaryCall,
    PrimaryIndex,
    PrimaryMember,
    ListCompLet,
    ListCompEach,
    ListCompFor,
    ListCompCFor,
    ListCompIf,
    ListCompIfElse,
    ListComprehension,
    ModularCall,
    ModularFor,
    ModularCFor,
    ModularIntersectionFor,
    ModularIntersectionCFor,
    ModularLet,
    ModularEcho,
    ModularAssert,
    ModularIf,
    ModularIfElse,
    ModularModifierShowOnly,
    ModularModifierHighlight,
    ModularModifierBackground,
    ModularModifierDisable,
    ModuleDeclaration,
    FunctionDeclaration,
    UseStatement,
    IncludeStatement,
)


def _pos():
    return Position(origin="<test>", line=1, column=1)


def _ident(name: str):
    return Identifier(name=name, position=_pos())


def _num(val: float):
    return NumberLiteral(val=val, position=_pos())


def test_basic_literals_str():
    assert str(CommentLine(text=" hello", position=_pos())) == "// hello"
    assert str(CommentSpan(text=" block ", position=_pos())) == "/* block */"
    assert str(_ident("foo")) == "foo"
    assert str(StringLiteral(val="bar", position=_pos())) == '"bar"'
    assert str(_num(1.5)) == "1.5"
    assert str(BooleanLiteral(val=True, position=_pos())) == "True"
    assert str(UndefinedLiteral(position=_pos())) == "undef"


def test_params_args_assignments_str():
    param_default = ParameterDeclaration(
        name=_ident("x"),
        default=_num(1.0),
        position=_pos(),
    )
    param_required = ParameterDeclaration(
        name=_ident("y"),
        default=None,
        position=_pos(),
    )
    assert str(param_default) == "x = 1.0"
    assert str(param_required).strip() == "y"

    pos_arg = PositionalArgument(expr=_num(2.0), position=_pos())
    named_arg = NamedArgument(name=_ident("z"), expr=_num(3.0), position=_pos())
    assert str(pos_arg) == "2.0"
    assert str(named_arg) == "z=3.0"

    assign = Assignment(name=_ident("a"), expr=_num(4.0), position=_pos())
    assert str(assign) == "a = 4.0"

    let_op = LetOp(assignments=[assign], body=_num(5.0), position=_pos())
    assert "let(" in str(let_op)
    assert "a = 4.0" in str(let_op)

    echo_op = EchoOp(arguments=[pos_arg], body=_num(6.0), position=_pos())
    assert "echo(" in str(echo_op)
    assert "2.0" in str(echo_op)

    assert_op = AssertOp(arguments=[named_arg], body=_num(7.0), position=_pos())
    assert "assert(" in str(assert_op)
    assert "z=3.0" in str(assert_op)


def test_operator_str():
    left = _num(1.0)
    right = _num(2.0)
    assert str(UnaryMinusOp(expr=left, position=_pos())) == "-1.0"
    assert str(AdditionOp(left=left, right=right, position=_pos())) == "1.0 + 2.0"
    assert str(SubtractionOp(left=left, right=right, position=_pos())) == "1.0 - 2.0"
    assert str(MultiplicationOp(left=left, right=right, position=_pos())) == "1.0 * 2.0"
    assert str(DivisionOp(left=left, right=right, position=_pos())) == "1.0 / 2.0"
    assert str(ModuloOp(left=left, right=right, position=_pos())) == "1.0 % 2.0"
    assert str(ExponentOp(left=left, right=right, position=_pos())) == "1.0 ^ 2.0"
    assert str(BitwiseAndOp(left=left, right=right, position=_pos())) == "1.0 & 2.0"
    assert str(BitwiseOrOp(left=left, right=right, position=_pos())) == "1.0 | 2.0"
    assert str(BitwiseNotOp(expr=left, position=_pos())) == "~1.0"
    assert str(BitwiseShiftLeftOp(left=left, right=right, position=_pos())) == "1.0 << 2.0"
    assert str(BitwiseShiftRightOp(left=left, right=right, position=_pos())) == "1.0 >> 2.0"
    assert str(LogicalAndOp(left=left, right=right, position=_pos())) == "1.0 && 2.0"
    assert str(LogicalOrOp(left=left, right=right, position=_pos())) == "1.0 || 2.0"
    assert str(LogicalNotOp(expr=left, position=_pos())) == "!1.0"
    assert str(TernaryOp(condition=left, true_expr=right, false_expr=left, position=_pos())) == "1.0 ? 2.0 : 1.0"
    assert str(EqualityOp(left=left, right=right, position=_pos())) == "1.0 == 2.0"
    assert str(InequalityOp(left=left, right=right, position=_pos())) == "1.0 != 2.0"
    assert str(GreaterThanOp(left=left, right=right, position=_pos())) == "1.0 > 2.0"
    assert str(GreaterThanOrEqualOp(left=left, right=right, position=_pos())) == "1.0 >= 2.0"
    assert str(LessThanOp(left=left, right=right, position=_pos())) == "1.0 < 2.0"
    assert str(LessThanOrEqualOp(left=left, right=right, position=_pos())) == "1.0 <= 2.0"


def test_primary_and_range_str():
    args = [PositionalArgument(expr=_num(3.0), position=_pos())]
    func_lit = FunctionLiteral(arguments=args, body=_num(4.0), position=_pos())
    assert str(func_lit) == "function(3.0) 4.0"

    call = PrimaryCall(left=_ident("foo"), arguments=args, position=_pos())
    assert str(call) == "foo(3.0)"

    idx = PrimaryIndex(left=_ident("arr"), index=_num(1.0), position=_pos())
    assert str(idx) == "arr[1.0]"

    member = PrimaryMember(left=_ident("obj"), member=_ident("x"), position=_pos())
    assert str(member) == "obj.x"

    range_lit = RangeLiteral(start=_num(0.0), end=_num(5.0), step=_num(1.0), position=_pos())
    assert str(range_lit) == "0.0:5.0:1.0"


def test_list_comprehension_str():
    assign = Assignment(name=_ident("i"), expr=_num(0.0), position=_pos())
    list_let = ListCompLet(assignments=[assign], body=_num(1.0), position=_pos())
    assert str(list_let).startswith("let (")
    assert "Assignment" in str(list_let)

    list_each = ListCompEach(body=_num(2.0), position=_pos())
    assert str(list_each) == "each 2.0"

    list_for = ListCompFor(assignments=[assign], body=_num(3.0), position=_pos())
    assert str(list_for).startswith("for (")

    list_c_for = ListCompCFor(
        initial=[assign],
        condition=_num(1.0),
        increment=[assign],
        body=_num(4.0),
        position=_pos(),
    )
    assert str(list_c_for).startswith("for (")
    assert "; " in str(list_c_for)

    list_if = ListCompIf(condition=_num(1.0), true_expr=_num(5.0), position=_pos())
    assert str(list_if) == "if 1.0 5.0"

    list_if_else = ListCompIfElse(condition=_num(1.0), true_expr=_num(6.0), false_expr=_num(7.0), position=_pos())
    assert str(list_if_else) == "if 1.0 6.0 else 7.0"

    list_comp = ListComprehension(elements=[list_if], position=_pos())
    assert str(list_comp) == "[if 1.0 5.0]"


def test_modular_and_declaration_str():
    pos_arg = PositionalArgument(expr=_num(1.0), position=_pos())
    mod_call = ModularCall(name=_ident("cube"), arguments=[pos_arg], children=[], position=_pos())
    assert str(mod_call) == "cube(1.0)"

    assign = Assignment(name=_ident("i"), expr=_num(0.0), position=_pos())
    mod_for = ModularFor(assignments=[assign], body=mod_call, position=_pos())
    assert str(mod_for).startswith("for (")

    mod_c_for = ModularCFor(initial=[assign], condition=_num(1.0), increment=[assign], body=mod_call, position=_pos())
    assert "for (" in str(mod_c_for)

    mod_int_for = ModularIntersectionFor(assignments=[assign], body=mod_call, position=_pos())
    assert str(mod_int_for).startswith("intersection_for")

    mod_int_c_for = ModularIntersectionCFor(initial=[assign], condition=_num(1.0), increment=[assign], body=mod_call, position=_pos())
    assert "intersection_for (" in str(mod_int_c_for)

    mod_let = ModularLet(assignments=[assign], children=[mod_call], position=_pos())
    assert "let (" in str(mod_let)

    mod_echo = ModularEcho(arguments=[pos_arg], children=[mod_call], position=_pos())
    assert "echo(" in str(mod_echo)

    mod_assert = ModularAssert(arguments=[pos_arg], children=[mod_call], position=_pos())
    assert "assert(" in str(mod_assert)

    mod_if = ModularIf(condition=_num(1.0), true_branch=mod_call, position=_pos())
    assert str(mod_if) == "if (1.0) cube(1.0)"

    mod_if_else = ModularIfElse(condition=_num(1.0), true_branch=mod_call, false_branch=mod_call, position=_pos())
    assert "if (1.0)" in str(mod_if_else)

    assert str(ModularModifierShowOnly(child=mod_call, position=_pos())) == "!cube(1.0)"
    assert str(ModularModifierHighlight(child=mod_call, position=_pos())) == "#cube(1.0)"
    assert str(ModularModifierBackground(child=mod_call, position=_pos())) == "%cube(1.0)"
    assert str(ModularModifierDisable(child=mod_call, position=_pos())) == "*cube(1.0)"

    mod_decl = ModuleDeclaration(name=_ident("m"), parameters=[], children=[mod_call], position=_pos())
    assert str(mod_decl) == "module m() { cube(1.0) }"

    func_decl = FunctionDeclaration(name=_ident("f"), parameters=[], expr=_num(2.0), position=_pos())
    assert str(func_decl) == "function f() = 2.0;"

    use_stmt = UseStatement(filepath=StringLiteral(val="lib.scad", position=_pos()), position=_pos())
    assert str(use_stmt) == "use <lib.scad>"

    include_stmt = IncludeStatement(filepath=StringLiteral(val="lib.scad", position=_pos()), position=_pos())
    assert str(include_stmt) == "include <lib.scad>"
