#######################################################################
# Arpeggio PEG Grammar for OpenSCAD
#######################################################################

from __future__ import unicode_literals

from arpeggio import (
    ParserPython, Optional, ZeroOrMore, OneOrMore, EOF, Kwd, Not, And,
    RegExMatch as _
)


# --- The parser ---

def getOpenSCADParser():
    return ParserPython(openscad_language, comment, reduce_tree=False, memoization=True, debug=False)


# --- OpenSCAD language parsing root ---

def openscad_language():
    return ( ZeroOrMore([ use_stmt, include_stmt, statement ]), EOF )


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
    return _(r'[+-]?(0x[0-9A-Fa-f]+|\d+([.]\d*)?([eE][+-]?\d+)?|[.]\d+([eE][+-]?\d+)?)')

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
    return ( '=', Not('=') )

def TOK_USE():
    return Kwd("use")

def TOK_INCLUDE():
    return Kwd("include")

def TOK_MODULE():
    return Kwd("module")

def TOK_FUNCTION():
    return Kwd("function")

def TOK_IF():
    return Kwd("if")

def TOK_ELSE():
    return Kwd("else")

def TOK_FOR():
    return Kwd("for")

def TOK_INTERSECTION_FOR():
    return Kwd("intersection_for")

def TOK_LET():
    return Kwd("let")

def TOK_ASSERT():
    return Kwd("assert")

def TOK_ECHO():
    return Kwd("echo")

def TOK_EACH():
    return Kwd("each")

def TOK_TRUE():
    return _(r'true\>')

def TOK_FALSE():
    return _(r'false\>')

def TOK_UNDEF():
    return _(r'undef\>')


# --- Grammar rules ---

def use_stmt():
    return ( TOK_USE, '<', _(r'[^>]+'), '>' )

def include_stmt():
    return ( TOK_INCLUDE, '<', _(r'[^>]+'), '>' )

def statement():
    return [
            ";",
            ( '{', ZeroOrMore(statement), '}' ),
            module_def,
            function_def,
            module_instance,
            assignment_stmt
        ]

def module_def():
    return (TOK_MODULE, TOK_ID, '(', parameters, ')', statement)

def function_def():
    return (TOK_FUNCTION, TOK_ID, '(', parameters, ')', TOK_ASSIGN, expr, ';')

def assignment_stmt():
    return (TOK_ID, TOK_ASSIGN, expr, ';')

def module_instance():
    return [
            modifier_show_only,
            modifier_highlight,
            modifier_background,
            modifier_disable,
            single_module_instance
        ]

def modifier_show_only():
    return ( '!', module_instance )

def modifier_highlight():
    return ( '#', module_instance )

def modifier_background():
    return ( '%', module_instance )

def modifier_disable():
    return ( '*', module_instance )

def single_module_instance():
    return [
            modular_for,
            modular_intersection_for,
            modular_ifelse,
            modular_let,
            modular_assert,
            modular_echo,
            modular_call
        ]

def child_stmt():
    return [
            ';',
            child_block,
            module_instance
        ]

def child_block():
    return ( '{', ZeroOrMore([ assignment_stmt, child_block ]), '}' )
    

# --- Modules and Module Control Structures ---

def modular_for():
    return  ( TOK_FOR, "(", assignments_expr, Optional(";", expr, ";", assignments_expr), ")", child_stmt )

def modular_intersection_for():
    return  ( TOK_INTERSECTION_FOR, "(", assignments_expr, ")", child_stmt )

def modular_ifelse():
    return ( TOK_IF, '(', expr, ')', child_stmt, Optional(TOK_ELSE, child_stmt) )

def modular_let():
    return  ( TOK_LET, "(", assignments_expr, ")", child_stmt )

def modular_assert():
    return  ( TOK_ASSERT, "(", arguments, ")", child_stmt )

def modular_echo():
    return  ( TOK_ECHO, "(", arguments, ")", child_stmt )

def modular_call():
    return  ( TOK_ID, "(", arguments, ")", child_stmt )


# --- Parameter and argument lists ---

def parameters():
    return ( ZeroOrMore(parameter, sep=TOK_COMMA), ZeroOrMore(TOK_COMMA) )

def parameter():
    return ( TOK_ID, Optional(TOK_ASSIGN, expr) )

def arguments():
    return ( ZeroOrMore(argument, sep=TOK_COMMA), ZeroOrMore(TOK_COMMA) )

def argument():
    return ( Optional(TOK_ID, TOK_ASSIGN), expr )


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
    return ( TOK_LET, '(', arguments, ')', expr )

def assert_expr():
    return ( TOK_ASSERT, '(', arguments, ')', Optional(expr) )

def echo_expr():
    return ( TOK_ECHO, '(', arguments, ')', Optional(expr) )

def funclit_def():
    return ( TOK_FUNCTION, '(', parameters, ')', expr )

def ternary_expr():
    return ( prec_logical_or, '?', expr, ':', expr )

def prec_logical_or():
    return OneOrMore(prec_logical_and, sep=TOK_LOGICAL_OR)

def prec_logical_and():
    return OneOrMore(prec_equality, sep=TOK_LOGICAL_AND)

def prec_equality():
    return OneOrMore(prec_relational, sep=[TOK_EQUAL, TOK_NOTEQUAL])

def prec_relational():
    return OneOrMore(prec_sum, sep=['<=', '>=', '<', '>'])

def prec_sum():
    return OneOrMore(prec_product, sep=['+', '-'])

def prec_product():
    return OneOrMore(prec_unary, sep=['*', '/', '%'])

def prec_unary():
    return ( ZeroOrMore(['+', '-', '!']), prec_power )

def prec_power():
    return ( prec_call, Optional('^', prec_unary) )

def prec_call():
    return ( primary, ZeroOrMore([call_expr, lookup_expr, member_expr]) )

def call_expr():
    return ( '(', arguments, ')' )

def lookup_expr():
    return ( '[', expr, ']' )

def member_expr():
    return ( '.', TOK_ID )

def primary():
    return [
            ( '(', expr, ')' ),
            range_literal,
            vector_decl,
            undef_literal,
            true_literal,
            false_literal,
            string_literal,
            number_literal,
            variable_access
        ]

def range_literal():
    return ( '[', expr, ':', Optional(expr, ':'), expr, ']' )

def vector_decl():
    return ( '[', vector_elements, Optional(TOK_COMMA), ']' )

def undef_literal():
    return TOK_UNDEF

def true_literal():
    return TOK_TRUE

def false_literal():
    return TOK_FALSE

def string_literal():
    return TOK_STRING

def number_literal():
    return TOK_NUMBER

def variable_access():
    return TOK_ID


# --- Vector and list comprehension ---

def vector_elements():
    return ZeroOrMore(vector_element, sep=TOK_COMMA)

def vector_element():
    return [ listcomp_elements_p, expr ]

def listcomp_elements_p():
    return [
            listcomp_elements,
            ( '(', listcomp_elements_p, ')' )
        ]

def listcomp_elements():
    return [
            listcomp_let,
            listcomp_each,
            listcomp_for,
            listcomp_ifelse,
        ]

def listcomp_let():
    return ( TOK_LET, '(', arguments, ')', listcomp_elements_p )

def listcomp_each():
    return ( TOK_EACH, vector_element )

def listcomp_for():
    return ( TOK_FOR, '(', assignments_expr, Optional(';', expr, ';', assignments_expr), ')', vector_element )

def listcomp_ifelse():
    return ( TOK_IF, '(', expr, ')', vector_element, Optional(TOK_ELSE, vector_element) )



