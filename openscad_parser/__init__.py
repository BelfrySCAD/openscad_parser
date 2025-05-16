#######################################################################
# Arpeggio PEG Grammar for OpenSCAD
#######################################################################

from __future__ import unicode_literals

from arpeggio import (
    ParserPython, Optional, ZeroOrMore, OneOrMore, EOF, Kwd, Not,  # And,
    RegExMatch as _
)


# --- The parser ---

def getOpenSCADParser(reduce_tree=False, debug=False):
    return ParserPython(
        openscad_language, comment, reduce_tree=reduce_tree,
        memoization=True, debug=debug
        )


# --- OpenSCAD language parsing root ---

def openscad_language():
    return (ZeroOrMore([use_statement, include_statement, statement]), EOF)


# --- Lexical and basic rules ---

def comment_line():
    return _(r'//.*?$', str_repr='comment')


def comment_multi():
    return _(r'(?ms)/\*.*?\*/', str_repr='comment')


def comment():
    return [comment_line, comment_multi]


def TOK_STRING():
    return [
            ("'", _(r"([^'\\]|\\.|\\$)*", str_repr='string'), "'"),
            ('"', _(r'([^"\\]|\\.|\\$)*', str_repr='string'), '"')
        ]


def TOK_NUMBER():
    return _(
        r'[+-]?(0x[0-9A-Fa-f]+|'
        r'\d+([.]\d*)?([eE][+-]?\d+)?'
        r'|[.]\d+([eE][+-]?\d+)?)',
        str_repr='number'
        )


def TOK_ID():
    return [_(r"([$]?[A-Za-z0-9_]+)", str_repr='string')]


def TOK_COMMA():
    return ','


def TOK_LOGICAL_OR():
    return "||"


def TOK_LOGICAL_AND():
    return "&&"


def TOK_EQUAL():
    return "=="


def TOK_NOTEQUAL():
    return "!="


def TOK_ASSIGN():
    return ('=', Not('='))


def TOK_USE():
    return Kwd('use')


def TOK_INCLUDE():
    return Kwd('include')


def TOK_MODULE():
    return Kwd('module')


def TOK_FUNCTION():
    return Kwd('function')


def TOK_IF():
    return Kwd('if')


def TOK_ELSE():
    return Kwd('else')


def TOK_FOR():
    return Kwd('for')


def TOK_INTERSECTION_FOR():
    return Kwd('intersection_for')


def TOK_LET():
    return Kwd('let')


def TOK_ASSERT():
    return Kwd('assert')


def TOK_ECHO():
    return Kwd('echo')


def TOK_EACH():
    return Kwd('each')


def TOK_TRUE():
    return _(r'true\>')


def TOK_FALSE():
    return _(r'false\>')


def TOK_UNDEF():
    return _(r'undef\>')


# --- Grammar rules ---

def use_statement():
    return (TOK_USE, '<', _(r'[^>]+'), '>')


def include_statement():
    return (TOK_INCLUDE, '<', _(r'[^>]+'), '>')


def statement():
    return [
            ";",
            ('{', ZeroOrMore(statement), '}'),
            module_definition,
            function_definition,
            module_instantiation,
            assignment
        ]


def module_definition():
    return (TOK_MODULE, TOK_ID, '(', parameters, ')', statement)


def function_definition():
    return (TOK_FUNCTION, TOK_ID, '(', parameters, ')', TOK_ASSIGN, expr, ';')


def assignment():
    return (TOK_ID, TOK_ASSIGN, expr, ';')


def module_instantiation():
    return [
            modifier_show_only,
            modifier_highlight,
            modifier_background,
            modifier_disable,
            ifelse_statement,
            single_module_instantiation
        ]


def modifier_show_only():
    return ('!', module_instantiation)


def modifier_highlight():
    return ('#', module_instantiation)


def modifier_background():
    return ('%', module_instantiation)


def modifier_disable():
    return ('*', module_instantiation)


def ifelse_statement():
    return [
            (TOK_IF, '(', expr, ')', child_statement,
                TOK_ELSE, child_statement),
            (TOK_IF, '(', expr, ')', child_statement)
        ]


def single_module_instantiation():
    return [
            modular_for,
            modular_intersection_for,
            modular_let,
            modular_assert,
            modular_echo,
            modular_call
        ]


def child_statement():
    return [
            ';',
            ('{', ZeroOrMore([assignment, child_statement]), '}'),
            module_instantiation
        ]


# --- Modules and Module Control Structures ---

def modular_for():
    return [
            (TOK_FOR, "(", assignments_expr, ")", child_statement),
            (TOK_FOR, "(", assignments_expr, ";", expr, ";", assignments_expr,
                ")", child_statement)
        ]


def modular_intersection_for():
    return (TOK_INTERSECTION_FOR, "(", assignments_expr, ")", child_statement)


def modular_let():
    return (TOK_LET, "(", arguments, ")", child_statement)


def modular_assert():
    return (TOK_ASSERT, "(", arguments, ")", child_statement)


def modular_echo():
    return (TOK_ECHO, "(", arguments, ")", child_statement)


def modular_call():
    return (TOK_ID, "(", arguments, ")", child_statement)


# --- Parameter and argument lists ---

def parameters():
    return (ZeroOrMore(parameter, sep=TOK_COMMA), ZeroOrMore(TOK_COMMA))


def parameter():
    return [
            (TOK_ID, TOK_ASSIGN, expr),
            TOK_ID
        ]


def arguments():
    return (ZeroOrMore(argument, sep=TOK_COMMA), Optional(TOK_COMMA))


def argument():
    return [
            (TOK_ID, TOK_ASSIGN, expr),
            expr
        ]


# --- Expressions ---

def assignments_expr():
    return ZeroOrMore(assignment_expr, sep=TOK_COMMA)


def assignment_expr():
    return (TOK_ID, TOK_ASSIGN, expr)


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
    return (TOK_LET, '(', assignments_expr, ')', expr)


def assert_expr():
    return (TOK_ASSERT, '(', arguments, ')', Optional(expr))


def echo_expr():
    return (TOK_ECHO, '(', arguments, ')', Optional(expr))


def funclit_def():
    return (TOK_FUNCTION, '(', parameters, ')', expr)


def ternary_expr():
    return (prec_logical_or, '?', expr, ':', expr)


def prec_logical_or():
    return OneOrMore(prec_logical_and, sep=TOK_LOGICAL_OR)


def prec_logical_and():
    return OneOrMore(prec_equality, sep=TOK_LOGICAL_AND)


def prec_equality():
    return OneOrMore(prec_comparison, sep=[TOK_EQUAL, TOK_NOTEQUAL])


def prec_comparison():
    return OneOrMore(prec_addition, sep=['<=', '>=', '<', '>'])


def prec_addition():
    return OneOrMore(prec_multiplication, sep=['+', '-'])


def prec_multiplication():
    return OneOrMore(prec_unary, sep=['*', '/', '%'])


def prec_unary():
    return (ZeroOrMore(['+', '-', '!']), prec_exponent)


def prec_exponent():
    return [
        (prec_call, '^', prec_unary),
        prec_call
    ]


def prec_call():
    return (primary, ZeroOrMore([call_expr, lookup_expr, member_expr]))


def call_expr():
    return ('(', arguments, ')')


def lookup_expr():
    return ('[', expr, ']')


def member_expr():
    return ('.', TOK_ID)


def primary():
    return [
            ('(', expr, ')'),
            ('[', expr, ':', expr, Optional(':', expr), ']'),
            ('[', vector_elements, Optional(TOK_COMMA), ']'),
            TOK_UNDEF,
            TOK_TRUE,
            TOK_FALSE,
            TOK_STRING,
            TOK_NUMBER,
            TOK_ID
        ]


# --- Vector and list comprehension ---

def vector_elements():
    return ZeroOrMore(vector_element, sep=TOK_COMMA)


def vector_element():
    return [listcomp_elements, expr]


def listcomp_elements():
    return [
            ('(', listcomp_elements, ')'),
            listcomp_let,
            listcomp_each,
            listcomp_for,
            listcomp_ifelse,
        ]


def listcomp_let():
    return (TOK_LET, '(', assignments_expr, ')', listcomp_elements)


def listcomp_each():
    return (TOK_EACH, vector_element)


def listcomp_for():
    return [
            (TOK_FOR, '(', assignments_expr, ';', expr, ';',
                assignments_expr, ')', vector_element),
            (TOK_FOR, '(', assignments_expr, ')', vector_element),
        ]


def listcomp_ifelse():
    return [
            (TOK_IF, '(', expr, ')', vector_element, TOK_ELSE, vector_element)
            (TOK_IF, '(', expr, ')', vector_element)
        ]


# vim: set ts=4 sw=4 expandtab:
