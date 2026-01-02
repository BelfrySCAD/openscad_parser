OpenSCAD Parser
===============

A PEG parser for the OpenSCAD language that can parse OpenSCAD source code and optionally generate an Abstract Syntax Tree (AST) for programmatic analysis and manipulation.

Features
--------

- Full OpenSCAD language support including:
  - Module and function definitions
  - Expressions with proper operator precedence
  - Control structures (if/else, for loops, let, assert, echo)
  - List comprehensions
  - Module modifiers (!, #, %, *)
  - Use and include statements
- Parse tree generation using Arpeggio PEG parser
- AST generation with comprehensive node types
- Source position tracking for all AST nodes
- AST tree can contain comment nodes (single-line and multi-line)
- AST tree uses dataclasses and can be pickled/unpickled for caching/serialization

Installation
------------

Install from PyPI::

    pip install openscad-parser

Or install from source::

    git clone https://github.com/belfryscad/openscad_parser.git
    cd openscad_parser
    pip install -e .

Basic Usage
-----------

Parsing OpenSCAD Code
~~~~~~~~~~~~~~~~~~~~~

To parse OpenSCAD code, first create a parser instance, then parse your code::

    from openscad_parser import getOpenSCADParser

    # Create a parser instance
    parser = getOpenSCADParser(reduce_tree=False)

    # Parse OpenSCAD code
    code = """
    module test(x, y=10) {
        cube([x, y, 5]);
        translate([0, 0, y]) sphere(5);
    }
    """

    parse_tree = parser.parse(code)

The parser returns an Arpeggio parse tree that represents the structure of your OpenSCAD code.

Parser Options
~~~~~~~~~~~~~~

The ``getOpenSCADParser()`` function accepts several options::

    parser = getOpenSCADParser(
        reduce_tree=False,  # Keep full parse tree (default: False)
        debug=False         # Enable debug output (default: False)
    )

- ``reduce_tree``: If True, reduces the parse tree by removing single-child nodes. Set to False when generating ASTs.
- ``debug``: If True, enables verbose debug output during parsing.

AST Generation
--------------

The parser can convert the parse tree into an Abstract Syntax Tree (AST) with typed nodes for easier programmatic manipulation.

Basic AST Generation
~~~~~~~~~~~~~~~~~~~~

To generate an AST from OpenSCAD code::

    from openscad_parser import getOpenSCADParser
    from openscad_parser.ast import parse_ast

    # Create a parser instance
    parser = getOpenSCADParser(reduce_tree=False)

    # Parse and generate AST
    code = "x = 10 + 5;"
    ast = parse_ast(parser, code)

    # ast is a list of top-level statements
    assignment = ast[0]
    print(assignment.name.name)  # "x"
    print(assignment.expr)       # AdditionOp(left=NumberLiteral(10), right=NumberLiteral(5))

The ``parse_ast()`` function is the main entry point for AST generation. It takes:

- ``parser``: An Arpeggio parser instance (from ``getOpenSCADParser()``)
- ``code``: The OpenSCAD code string to parse
- ``file``: Optional file path for source location tracking

Working with AST Nodes
~~~~~~~~~~~~~~~~~~~~~~

All AST nodes inherit from ``ASTNode`` and have a ``position`` attribute for source location tracking::

    from openscad_parser.ast import (
        Assignment, Identifier, NumberLiteral, AdditionOp
    )

    code = "result = 10 + 20;"
    ast = parse_ast(parser, code)
    assignment = ast[0]

    # Check node types
    assert isinstance(assignment, Assignment)
    assert isinstance(assignment.name, Identifier)
    assert isinstance(assignment.expr, AdditionOp)

    # Access node properties
    print(assignment.name.name)           # "result"
    print(assignment.expr.left.val)      # 10
    print(assignment.expr.right.val)      # 20

    # Access source position
    print(assignment.position.line)      # Line number (1-indexed)
    print(assignment.position.char)      # Column number (1-indexed)

Examples
--------

Parsing a Simple Assignment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from openscad_parser import getOpenSCADParser
    from openscad_parser.ast import parse_ast, Assignment, Identifier

    parser = getOpenSCADParser(reduce_tree=False)
    code = "x = 42;"
    ast = parse_ast(parser, code)

    assignment = ast[0]
    assert isinstance(assignment, Assignment)
    assert assignment.name.name == "x"
    assert assignment.expr.val == 42

Parsing a Module Definition
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    from openscad_parser import getOpenSCADParser
    from openscad_parser.ast import parse_ast, ModuleDeclaration, ModularCall

    parser = getOpenSCADParser(reduce_tree=False)
    code = """
    module box(size) {
        cube(size);
    }
    """

    ast = parse_ast(parser, code)
    module = ast[0]

    assert isinstance(module, ModuleDeclaration)
    assert module.name.name == "box"
    assert len(module.parameters) == 1
    assert len(module.children) == 1
    assert isinstance(module.children[0], ModularCall)
    assert module.children[0].name.name == "cube"

Parsing Expressions
~~~~~~~~~~~~~~~~~~~

::

    from openscad_parser import getOpenSCADParser
    from openscad_parser.ast import (
        parse_ast, Assignment, AdditionOp, MultiplicationOp, NumberLiteral
    )

    parser = getOpenSCADParser(reduce_tree=False)
    code = "result = (10 + 5) * 2;"
    ast = parse_ast(parser, code)

    assignment = ast[0]
    # The expression tree preserves operator precedence
    mult_op = assignment.expr
    assert isinstance(mult_op, MultiplicationOp)
    assert isinstance(mult_op.left, AdditionOp)
    assert mult_op.left.left.val == 10
    assert mult_op.left.right.val == 5
    assert mult_op.right.val == 2

Parsing Function Calls
~~~~~~~~~~~~~~~~~~~~~~

::

    from openscad_parser import getOpenSCADParser
    from openscad_parser.ast import (
        parse_ast, PrimaryCall, PositionalArgument, NamedArgument
    )

    parser = getOpenSCADParser(reduce_tree=False)
    code = "x = foo(1, b=2);"
    ast = parse_ast(parser, code)

    assignment = ast[0]
    call = assignment.expr
    assert isinstance(call, PrimaryCall)
    assert call.left.name == "foo"
    assert len(call.arguments) == 2
    assert isinstance(call.arguments[0], PositionalArgument)
    assert isinstance(call.arguments[1], NamedArgument)
    assert call.arguments[1].name.name == "b"

AST Node Types
--------------

The AST includes comprehensive node types for all OpenSCAD language constructs:

Base Classes
~~~~~~~~~~~~

- ``ASTNode``: Base class for all AST nodes (includes ``position`` attribute)
- ``Expression``: Base class for all expression nodes
- ``Primary``: Base class for atomic value types
- ``ModuleInstantiation``: Base class for module-related statements

Literals
~~~~~~~~

- ``Identifier``: Variable, function, or module names
- ``StringLiteral``: String values
- ``NumberLiteral``: Numeric values
- ``BooleanLiteral``: true/false values
- ``UndefinedLiteral``: undef value
- ``RangeLiteral``: Range expressions [start:end:step]

Operators
~~~~~~~~~

Arithmetic:
- ``AdditionOp``, ``SubtractionOp``, ``MultiplicationOp``, ``DivisionOp``
- ``ModuloOp``, ``ExponentOp``, ``UnaryMinusOp``

Logical:
- ``LogicalAndOp``, ``LogicalOrOp``, ``LogicalNotOp``

Comparison:
- ``EqualityOp``, ``InequalityOp``
- ``GreaterThanOp``, ``GreaterThanOrEqualOp``
- ``LessThanOp``, ``LessThanOrEqualOp``

Bitwise:
- ``BitwiseAndOp``, ``BitwiseOrOp``, ``BitwiseNotOp``
- ``BitwiseShiftLeftOp``, ``BitwiseShiftRightOp``

Other:
- ``TernaryOp``: condition ? true_expr : false_expr

Expressions
~~~~~~~~~~~

- ``LetOp``: let(assignments) body
- ``EchoOp``: echo(arguments) body
- ``AssertOp``: assert(arguments) body
- ``FunctionLiteral``: function(parameters) body
- ``PrimaryCall``: function calls
- ``PrimaryIndex``: array indexing [index]
- ``PrimaryMember``: member access .member

List Comprehensions
~~~~~~~~~~~~~~~~~~~

- ``ListComprehension``: Vector/list literals
- ``ListCompFor``: for loops in list comprehensions
- ``ListCompCStyleFor``: C-style for loops
- ``ListCompIf``, ``ListCompIfElse``: Conditionals
- ``ListCompLet``: let expressions
- ``ListCompEach``: each expressions

Module Instantiations
~~~~~~~~~~~~~~~~~~~~~

- ``ModularCall``: Module calls with arguments and children
- ``ModularFor``: for loops
- ``ModularCLikeFor``: C-style for loops
- ``ModularIntersectionFor``: intersection_for loops
- ``ModularLet``: let statements
- ``ModularEcho``: echo statements
- ``ModularAssert``: assert statements
- ``ModularIf``, ``ModularIfElse``: if/else statements
- ``ModularModifierShowOnly``: ! modifier
- ``ModularModifierHighlight``: # modifier
- ``ModularModifierBackground``: % modifier
- ``ModularModifierDisable``: * modifier

Declarations
~~~~~~~~~~~~

- ``ModuleDeclaration``: module definitions
- ``FunctionDeclaration``: function definitions
- ``ParameterDeclaration``: function/module parameters
- ``Assignment``: variable assignments

Statements
~~~~~~~~~~

- ``UseStatement``: use <filepath>
- ``IncludeStatement``: include <filepath>
- ``PositionalArgument``: Function call positional arguments
- ``NamedArgument``: Function call named arguments (name=value)

Comments
~~~~~~~~

- ``CommentLine``: Single-line comments //
- ``CommentSpan``: Multi-line comments /* */

All AST node classes are fully documented with docstrings that include:
- Description of what the node represents
- OpenSCAD code examples
- Field/attribute descriptions
- Usage notes

API Reference
-------------

Main Functions
~~~~~~~~~~~~~~

``getOpenSCADParser(reduce_tree=False, debug=False)``
    Create an Arpeggio parser instance for OpenSCAD code.

    :param reduce_tree: If True, reduces single-child nodes in parse tree
    :param debug: If True, enables debug output
    :returns: ParserPython instance

``parse_ast(parser, code, file="")``
    Parse OpenSCAD code and generate an AST.

    :param parser: Arpeggio parser instance from getOpenSCADParser()
    :param code: OpenSCAD code string to parse
    :param file: Optional file path for source location tracking
    :returns: AST node or list of AST nodes (for top-level statements)

AST Node Classes
~~~~~~~~~~~~~~~

All AST node classes are located in ``openscad_parser.ast``. Each node class:

- Inherits from ``ASTNode`` (or a subclass like ``Expression``)
- Has a ``position`` attribute of type ``Position`` for source location
- Implements ``__str__()`` for string representation
- Is a dataclass with typed fields

Import commonly used classes::

    from openscad_parser.ast import (
        # Base classes
        ASTNode, Expression, Primary,
        
        # Literals
        Identifier, StringLiteral, NumberLiteral, BooleanLiteral,
        
        # Operators
        AdditionOp, SubtractionOp, MultiplicationOp, DivisionOp,
        LogicalAndOp, LogicalOrOp, EqualityOp, InequalityOp,
        
        # Expressions
        PrimaryCall, PrimaryIndex, PrimaryMember,
        LetOp, EchoOp, AssertOp, TernaryOp,
        
        # Modules
        ModuleDeclaration, ModularCall, ModularFor,
        
        # Functions
        FunctionDeclaration,
        
        # Statements
        Assignment, UseStatement, IncludeStatement,
        PositionalArgument, NamedArgument, ParameterDeclaration
    )

Source Position Tracking
-------------------------

All AST nodes include source position information::

    from openscad_parser.ast import Position

    code = "x = 10;"
    ast = parse_ast(parser, code, file="example.scad")
    assignment = ast[0]

    position = assignment.position
    print(position.file)      # "example.scad"
    print(position.line)      # 1 (1-indexed)
    print(position.char)      # 1 (1-indexed, column number)
    print(position.position)  # 0 (0-indexed character position)

The ``Position`` class provides lazy evaluation of line/column numbers from character positions.

Error Handling
--------------

The parser will raise ``SyntaxError`` exceptions for invalid OpenSCAD syntax::

    try:
        code = "x = ;"  # Invalid syntax
        ast = parse_ast(parser, code)
    except SyntaxError as e:
        print(f"Parse error: {e}")

Advanced Usage
--------------

Reusing Parser Instances
~~~~~~~~~~~~~~~~~~~~~~~

Parser instances can be reused for parsing multiple code snippets::

    parser = getOpenSCADParser(reduce_tree=False)

    # Parse multiple files
    ast1 = parse_ast(parser, code1, file="file1.scad")
    ast2 = parse_ast(parser, code2, file="file2.scad")

Note: For some use cases (like testing), you may need to create fresh parser instances to avoid memoization issues.

Traversing the AST
~~~~~~~~~~~~~~~~~~

The AST is a tree structure that can be traversed recursively::

    def visit_node(node):
        """Recursively visit AST nodes."""
        if isinstance(node, Assignment):
            print(f"Assignment: {node.name.name}")
            visit_node(node.expr)
        elif isinstance(node, AdditionOp):
            print("Addition operation")
            visit_node(node.left)
            visit_node(node.right)
        elif isinstance(node, NumberLiteral):
            print(f"Number: {node.val}")
        # ... handle other node types

    ast = parse_ast(parser, code)
    for node in ast:
        visit_node(node)

Testing
-------

The project includes a comprehensive test suite. Run tests with::

    pytest tests/

Development
-----------

Contributions are welcome! The project uses:

- `Arpeggio <https://github.com/textX/Arpeggio>`_ for PEG parsing
- `pytest <https://pytest.org/>`_ for testing

License
-------

MIT License - see LICENSE file for details.

Links
-----

- `GitHub Repository <https://github.com/belfryscad/openscad_parser>`_
- `Issue Tracker <https://github.com/belfryscad/openscad_parser/issues>`_
- `Releases <https://github.com/belfryscad/openscad_parser/releases>`_

