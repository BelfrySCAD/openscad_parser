#######################################################################
# Arpeggio PEG Grammar for OpenSCAD
#######################################################################

from __future__ import unicode_literals

from arpeggio import (
    Optional, ZeroOrMore, OneOrMore, EOF, Kwd, Not,  # And,
    RegExMatch as _
)


# --- OpenSCAD language parsing root ---

def openscad_language():
    return (ZeroOrMore(toplevel_statement), EOF)


def openscad_language_with_comments():
    """Version of openscad_language that includes comments in the AST."""
    return (ZeroOrMore(toplevel_statement_or_comment), EOF)


def toplevel_statement():
    return [use_statement, include_statement, statement]


def toplevel_statement_or_comment():
    return [use_statement, include_statement, statement, comment]


# --- Lexical and basic rules ---

def comment_line():
    return _(r'//.*?$', str_repr='comment')


def comment_multi():
    return _(r'(?ms)/\*.*?\*/', str_repr='comment')


def comment():
    return [comment_line, comment_multi]


def whitespace_only():
    """Whitespace rule that only matches whitespace characters (spaces, tabs, newlines), not comments."""
    return _(r'[ \t\n\r]+')


# --- Tokens ---

def TOK_ID():
    return _(r"(\$?[_A-Za-z][A-Za-z0-9_]*)", str_repr='string')


def TOK_NUMBER():
    return _(
        r'[+-]?(0x[0-9A-Fa-f]+|'
        r'\d+([.]\d*)?([eE][+-]?\d+)?'
        r'|[.]\d+([eE][+-]?\d+)?)'
        )


def TOK_DQUOTE():
    return '"'


def TOK_COMMA():
    return ','


def TOK_COLON():
    return ':'


def TOK_SEMICOLON():
    return ';'


def TOK_LOGICAL_OR():
    return "||"


def TOK_LOGICAL_AND():
    return "&&"


def TOK_LOGICAL_NOT():
    return ("!", Not('='))


def TOK_BINARY_OR():
    return ("|", Not('|'))


def TOK_BINARY_AND():
    return ("&", Not('&'))


def TOK_BINARY_NOT():
    return "~"


def TOK_BINARY_SHIFT_LEFT():
    return "<<"


def TOK_BINARY_SHIFT_RIGHT():
    return ">>"


def TOK_GT():
    return (">", Not('>', '='))


def TOK_LT():
    return ("<", Not('<', '='))


def TOK_GTE():
    return ">="


def TOK_LTE():
    return "<="


def TOK_EQUAL():
    return "=="


def TOK_NOTEQUAL():
    return "!="


def TOK_ASSIGN():
    return ('=', Not('='))


def TOK_QUESTION():
    return '?'


def TOK_PERIOD():
    return '.'


def TOK_PAREN():
    return '('


def TOK_ENDPAREN():
    return ')'


def TOK_BRACE():
    return '{'


def TOK_ENDBRACE():
    return '}'


def TOK_BRACKET():
    return '['


def TOK_ENDBRACKET():
    return ']'


def TOK_ADD():
    return '+'


def TOK_SUBTRACT():
    return '-'


def TOK_MULTIPLY():
    return '*'


def TOK_DIVIDE():
    return '/'


def TOK_MODULO():
    return '%'


def TOK_EXPONENT():
    return '^'


# --- Modular Modifiers ---

def MOD_SHOW_ONLY():
    return '!'


def MOD_HIGHLIGHT():
    return '#'


def MOD_BACKGROUND():
    return '%'


def MOD_DISABLE():
    return '*'


# --- Keywords ---

def KWD_USE():
    return Kwd('use')


def KWD_INCLUDE():
    return Kwd('include')


def KWD_MODULE():
    return Kwd('module')


def KWD_FUNCTION():
    return Kwd('function')


def KWD_IF():
    return Kwd('if')


def KWD_ELSE():
    return Kwd('else')


def KWD_FOR():
    return Kwd('for')


def KWD_INTERSECTION_FOR():
    return Kwd('intersection_for')


def KWD_LET():
    return Kwd('let')


def KWD_ASSERT():
    return Kwd('assert')


def KWD_ECHO():
    return Kwd('echo')


def KWD_EACH():
    return Kwd('each')


def KWD_TRUE():
    return Kwd('true')


def KWD_FALSE():
    return Kwd('false')


def KWD_UNDEF():
    return Kwd('undef')


# --- Identifiers ---

def module_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


def function_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


def variable_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


def module_instantiation_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


def member_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


def variable_or_function_name():
    return (TOK_ID,)  # Tuple to prevent eliding the identifier


# --- Grammar rules ---


def use_include_file():
    return (TOK_LT, _(r'[^>]*', str_repr='string'), TOK_GT)


def use_statement():
    return (KWD_USE, use_include_file)


def include_statement():
    return (KWD_INCLUDE, use_include_file)


def statement():
    return [
            empty_statement,
            statement_block,
            module_definition,
            function_definition,
            module_instantiation,
            assignment
        ]


def empty_statement():
    return TOK_SEMICOLON


def statement_block():
    return (TOK_BRACE, ZeroOrMore(statement), TOK_ENDBRACE)


def module_definition():
    return (KWD_MODULE, module_name, parameter_block, statement)


def function_definition():
    return (KWD_FUNCTION, function_name, parameter_block, TOK_ASSIGN, expr, TOK_SEMICOLON)


def assignment():
    return (variable_name, TOK_ASSIGN, expr, TOK_SEMICOLON)


def module_instantiation():
    return [
            modifier_show_only,
            modifier_highlight,
            modifier_background,
            modifier_disable,
            ifelse_statement,
            if_statement,
            single_module_instantiation
        ]


def modifier_show_only():
    return (MOD_SHOW_ONLY, module_instantiation)


def modifier_highlight():
    return (MOD_HIGHLIGHT, module_instantiation)


def modifier_background():
    return (MOD_BACKGROUND, module_instantiation)


def modifier_disable():
    return (MOD_DISABLE, module_instantiation)


def if_statement():
    return (KWD_IF, TOK_PAREN, expr, TOK_ENDPAREN, child_statement)


def ifelse_statement():
    return (KWD_IF, TOK_PAREN, expr, TOK_ENDPAREN, child_statement, KWD_ELSE, child_statement)


def single_module_instantiation():
    return [
            modular_c_for,
            modular_for,
            modular_intersection_c_for,
            modular_intersection_for,
            modular_let,
            modular_assert,
            modular_echo,
            modular_call
        ]


def child_statement():
    return [
            empty_statement,
            statement_block,
            module_instantiation
        ]


# --- Modules and Module Control Structures ---

def modular_for():
    return (KWD_FOR, TOK_PAREN, assignments_expr, TOK_ENDPAREN, child_statement)


def modular_c_for():
    return (
        KWD_FOR,
        TOK_PAREN,
        assignments_expr,
        TOK_SEMICOLON,
        expr,
        TOK_SEMICOLON,
        assignments_expr,
        TOK_ENDPAREN,
        child_statement
    )


def modular_intersection_for():
    return (KWD_INTERSECTION_FOR, TOK_PAREN, assignments_expr, TOK_ENDPAREN, child_statement)


def modular_intersection_c_for():
    return (
        KWD_INTERSECTION_FOR,
        TOK_PAREN,
        assignments_expr,
        TOK_SEMICOLON,
        expr,
        TOK_SEMICOLON,
        assignments_expr,
        TOK_ENDPAREN,
        child_statement
    )


def modular_let():
    return (KWD_LET, TOK_PAREN, assignments_expr, TOK_ENDPAREN, child_statement)


def modular_assert():
    return (KWD_ASSERT, TOK_PAREN, arguments, TOK_ENDPAREN, child_statement)


def modular_echo():
    return (KWD_ECHO, TOK_PAREN, arguments, TOK_ENDPAREN, child_statement)


def modular_call():
    return (module_instantiation_name, TOK_PAREN, arguments, TOK_ENDPAREN, child_statement)


# --- Parameters used to define functions and modules ---


def parameter_block():
    return (TOK_PAREN, parameters, TOK_ENDPAREN)


def parameters():
    return (ZeroOrMore(parameter, sep=TOK_COMMA), ZeroOrMore(TOK_COMMA))


def parameter():
    return [
            parameter_with_default,
            parameter_without_default
        ]


def parameter_with_default():
    return (variable_name, TOK_ASSIGN, expr)


def parameter_without_default():
    return (variable_name, Not(TOK_ASSIGN))


# --- Arguments used when calling functions and modules ---

def argument_block():
    return (TOK_PAREN, arguments, TOK_ENDPAREN)


def arguments():
    return (ZeroOrMore(argument, sep=TOK_COMMA), Optional(TOK_COMMA))


def argument():
    return [
            named_argument,
            positional_argument
        ]


def positional_argument():
    return (expr, Not(TOK_ASSIGN))


def named_argument():
    return (variable_name, TOK_ASSIGN, expr)


# --- Expressions ---

def assignments_expr():
    return (ZeroOrMore(assignment_expr, sep=TOK_COMMA), Optional(TOK_COMMA))


def assignment_expr():
    return (variable_name, TOK_ASSIGN, expr)


def expr():
    return [
            let_expr,
            assert_expr,
            echo_expr,
            funclit_def,
            ternary_expr,
            prec_logical_or
        ]


def let_expr():
    return (KWD_LET, TOK_PAREN, assignments_expr, TOK_ENDPAREN, expr)


def assert_expr():
    return (KWD_ASSERT, TOK_PAREN, arguments, TOK_ENDPAREN, Optional(expr))


def echo_expr():
    return (KWD_ECHO, TOK_PAREN, arguments, TOK_ENDPAREN, Optional(expr))


def funclit_def():
    return (KWD_FUNCTION, TOK_PAREN, parameters, TOK_ENDPAREN, expr)


def ternary_expr():
    return (prec_logical_or, TOK_QUESTION, expr, TOK_COLON, expr)


def prec_logical_or():
    return OneOrMore(prec_logical_and, sep=TOK_LOGICAL_OR)


def prec_logical_and():
    return OneOrMore(prec_equality, sep=TOK_LOGICAL_AND)


def prec_equality():
    return OneOrMore(prec_comparison, sep=[TOK_EQUAL, TOK_NOTEQUAL])


def prec_comparison():
    return OneOrMore(prec_binary_or, sep=[TOK_LTE, TOK_GTE, TOK_LT, TOK_GT])


def prec_binary_or():
    return OneOrMore(prec_binary_and, sep=TOK_BINARY_OR)


def prec_binary_and():
    return OneOrMore(prec_binary_shift, sep=TOK_BINARY_AND)


def prec_binary_shift():
    return OneOrMore(prec_addition, sep=[TOK_BINARY_SHIFT_LEFT, TOK_BINARY_SHIFT_RIGHT])


def prec_addition():
    return OneOrMore(prec_multiplication, sep=[TOK_ADD, TOK_SUBTRACT])


def prec_multiplication():
    return OneOrMore(prec_unary, sep=[TOK_MULTIPLY, TOK_DIVIDE, TOK_MODULO])


def prec_unary():
    return (ZeroOrMore(['+', '-', TOK_LOGICAL_NOT, TOK_BINARY_NOT]), prec_exponent)


def prec_exponent():
    return [
        (prec_call, TOK_EXPONENT, prec_unary),
        prec_call
    ]


def prec_call():
    return (primary, ZeroOrMore([call_expr, lookup_expr, member_expr]))


def call_expr():
    return (argument_block,)


def lookup_expr():
    return (TOK_BRACKET, expr, TOK_ENDBRACKET)


def member_expr():
    return (TOK_PERIOD, member_name)


def string_contents():
    return _(r'([^"\\]|\\.|\\$)*', str_repr='string')


def string_literal():
    return (TOK_DQUOTE, string_contents, TOK_DQUOTE)


def primary():
    return [
            paren_expr,
            range_expr,
            vector_expr,
            include_statement,
            KWD_UNDEF,
            KWD_TRUE,
            KWD_FALSE,
            string_literal,
            TOK_NUMBER,
            variable_or_function_name
        ]


def paren_expr():
    return (TOK_PAREN, expr, TOK_ENDPAREN)


def range_expr():
    return (TOK_BRACKET, expr, TOK_COLON, expr, Optional(TOK_COLON, expr), TOK_ENDBRACKET)


def vector_expr():
    return (TOK_BRACKET, vector_elements, Optional(TOK_COMMA), TOK_ENDBRACKET)


# --- Vector and list comprehension ---

def vector_elements():
    return ZeroOrMore(vector_element, sep=TOK_COMMA)


def vector_element():
    return [listcomp_elements, expr]


def listcomp_elements():
    return [
            listcomp_paren_expr,
            listcomp_let,
            listcomp_each,
            listcomp_c_for,
            listcomp_for,
            listcomp_ifelse,
            listcomp_ifonly,
        ]


def listcomp_paren_expr():
    return (TOK_PAREN, listcomp_elements, TOK_ENDPAREN)


def listcomp_let():
    return (KWD_LET, TOK_PAREN, assignments_expr, TOK_ENDPAREN, listcomp_elements)


def listcomp_each():
    return (KWD_EACH, vector_element)


def listcomp_for():
    return (KWD_FOR, TOK_PAREN, assignments_expr, TOK_ENDPAREN, vector_element)


def listcomp_c_for():
    return (KWD_FOR, TOK_PAREN, assignments_expr, TOK_SEMICOLON, expr, TOK_SEMICOLON, assignments_expr, TOK_ENDPAREN, vector_element)


def listcomp_ifonly():
    return (KWD_IF, TOK_PAREN, expr, TOK_ENDPAREN, vector_element)


def listcomp_ifelse():
    return (KWD_IF, TOK_PAREN, expr, TOK_ENDPAREN, vector_element, KWD_ELSE, vector_element)


# vim: set ts=4 sw=4 expandtab:

