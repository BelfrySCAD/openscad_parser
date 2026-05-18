OpenSCAD Parser
===============

.. image:: https://raw.githubusercontent.com/BelfrySCAD/openscad_parser/main/coverage-badge.svg
   :alt: Coverage

A PEG parser for the OpenSCAD language that can parse OpenSCAD source code and optionally generate an Abstract Syntax Tree (AST) for programmatic analysis and manipulation.

Features
--------

- Full OpenSCAD language support including:
  - Module and function definitions
  - Expressions with proper operator precedence
  - Control structures (if/else, for loops, let, assert, echo)
  - List comprehensions
  - Module modifiers (``!``, ``#``, ``%``, ``*``)
  - Use and include statements
- Parse tree generation using Arpeggio PEG parser
- AST generation with comprehensive node types
- Source position tracking for all AST nodes
- AST tree can contain comment nodes (single-line and multi-line)
- AST tree uses dataclasses and can be pickled/unpickled for caching/serialization
- JSON and YAML serialization/deserialization of AST trees
- Pretty-printer that converts an AST back to formatted OpenSCAD source (``to_openscad()``)
- Command-line interface (``openscad-parser``) for JSON/YAML/formatted output

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

Convenience Functions
~~~~~~~~~~~~~~~~~~~~~

The easiest way to generate ASTs is using the convenience functions that handle parser creation automatically:

Parsing from a String
^^^^^^^^^^^^^^^^^^^^^^

Use ``getASTfromString()`` to parse OpenSCAD code from a string::

    from openscad_parser.ast import getASTfromString

    code = "x = 10 + 5;"
    ast = getASTfromString(code)

    # ast is a list of top-level statements
    assignment = ast[0]
    print(assignment.name.name)  # "x"
    print(assignment.expr)         # AdditionOp(left=NumberLiteral(10), right=NumberLiteral(5))

Parsing from a File
^^^^^^^^^^^^^^^^^^^^

Use ``getASTfromFile()`` to parse an OpenSCAD file. This function includes automatic caching - files are only re-parsed if their modification timestamp changes::

    from openscad_parser.ast import getASTfromFile

    # Parse a file (cached automatically)
    ast = getASTfromFile("my_model.scad")

    # Subsequent calls return cached AST if file hasn't changed
    ast2 = getASTfromFile("my_model.scad")  # Returns cached version

The cache is automatically invalidated when the file is modified, ensuring you always get up-to-date results.

**Include Processing:** By default, ``getASTfromFile()`` processes ``include <file>`` statements before parsing (``process_includes=True``). This means the AST will NOT contain ``IncludeStatement`` nodes - instead, the included file contents are expanded into the AST. Set ``process_includes=False`` to preserve ``IncludeStatement`` nodes in the AST::

    # Get AST with IncludeStatement nodes preserved
    ast_with_includes = getASTfromFile("my_model.scad", process_includes=False)

**Note:** Unlike ``include`` statements, ``use <file>`` statements are ALWAYS parsed into ``UseStatement`` AST nodes, regardless of the ``process_includes`` setting. This is because ``use`` statements only affect module and function lookup at runtime, not source inclusion.

Parsing Library Files
^^^^^^^^^^^^^^^^^^^^^^

Use ``getASTfromLibraryFile()`` to find and parse library files using OpenSCAD's search path rules. This is useful for resolving ``use`` and ``include`` statements::

    from openscad_parser.ast import getASTfromLibraryFile

    # From a file that includes a library
    # Searches: current file directory, OPENSCADPATH, platform defaults
    # Returns: (AST, absolute_path) tuple
    ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad")

    # Or without current file context
    ast, path = getASTfromLibraryFile("", "MCAD/boxes.scad")

The function searches for library files in this order:

1. Directory of the current file (if provided)
2. Directories in the ``OPENSCADPATH`` environment variable
3. Platform-specific default library directories:
   - Windows: ``~/Documents/OpenSCAD/libraries``
   - macOS: ``~/Documents/OpenSCAD/libraries``
   - Linux: ``~/.local/share/OpenSCAD/libraries``

Advanced AST Generation
~~~~~~~~~~~~~~~~~~~~~~~~

For more control, you can use ``parse_ast()`` directly with a custom parser instance::

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

The ``parse_ast()`` function is the lower-level API for AST generation. It takes:

- ``parser``: An Arpeggio parser instance (from ``getOpenSCADParser()``)
- ``code``: The OpenSCAD code string to parse
- ``file``: Optional file path for source location tracking

Working with AST Nodes
~~~~~~~~~~~~~~~~~~~~~~

All AST nodes inherit from ``ASTNode`` and have a ``position`` attribute for source location tracking::

    from openscad_parser.ast import (
        getASTfromString, Assignment, Identifier, NumberLiteral, AdditionOp
    )

    code = "result = 10 + 20;"
    ast = getASTfromString(code)
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
    print(assignment.position.column)    # Column number (1-indexed)

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

From a file::

    from openscad_parser.ast import getASTfromFile, ModuleDeclaration, ModularCall

    ast = getASTfromFile("box.scad")
    module = ast[0]

    assert isinstance(module, ModuleDeclaration)
    assert module.name.name == "box"
    assert len(module.parameters) == 1
    assert len(module.children) == 1
    assert isinstance(module.children[0], ModularCall)
    assert module.children[0].name.name == "cube"

Or from a string::

    from openscad_parser.ast import getASTfromString, ModuleDeclaration, ModularCall

    code = """
    module box(size) {
        cube(size);
    }
    """

    ast = getASTfromString(code)
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

    from openscad_parser.ast import (
        getASTfromString, Assignment, AdditionOp, MultiplicationOp, NumberLiteral
    )

    code = "result = (10 + 5) * 2;"
    ast = getASTfromString(code)

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

    from openscad_parser.ast import (
        getASTfromString, PrimaryCall, PositionalArgument, NamedArgument
    )

    code = "x = foo(1, b=2);"
    ast = getASTfromString(code)

    assignment = ast[0]
    call = assignment.expr
    assert isinstance(call, PrimaryCall)
    assert call.left.name == "foo"
    assert len(call.arguments) == 2
    assert isinstance(call.arguments[0], PositionalArgument)
    assert isinstance(call.arguments[1], NamedArgument)
    assert call.arguments[1].name.name == "b"

Parsing Library Files
~~~~~~~~~~~~~~~~~~~~~

::

    from openscad_parser.ast import getASTfromLibraryFile, ModuleDeclaration

    # Parse a library file using OpenSCAD's search path
    # Searches: current file dir, OPENSCADPATH, platform defaults
    # Returns: (AST, absolute_path) tuple
    ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad")

    # Or without current file context
    ast, path = getASTfromLibraryFile("", "MCAD/boxes.scad")

AST Node Types
--------------

The AST includes comprehensive node types for all OpenSCAD language constructs.
All nodes inherit from ``ASTNode`` and carry ``position: Position`` and ``scope: Scope | None`` attributes.

Base Classes
~~~~~~~~~~~~

- ``ASTNode(position: Position, scope: Scope | None)``: Base class for all AST nodes
- ``Expression``: Base class for all expression nodes
- ``Primary``: Base class for atomic value types (extends ``Expression``)
- ``ModuleInstantiation``: Base class for module-related statements
- ``VectorElement``: Base class for list comprehension elements

Literals
~~~~~~~~

- ``Identifier(name: str)``: Variable, function, or module names
- ``StringLiteral(val: str)``: String values
- ``NumberLiteral(val: float)``: Numeric values
- ``BooleanLiteral(val: bool)``: true/false values
- ``UndefinedLiteral``: The ``undef`` value (no additional fields)
- ``RangeLiteral(start: Expression, end: Expression, step: Expression)``: Range expressions ``[start:step:end]``

Operators
~~~~~~~~~

All operators inherit from ``Expression`` and represent their respective operations with typed fields for operands. The AST preserves operator precedence and associativity as defined in OpenSCAD.

Arithmetic:

- ``AdditionOp(left: Expression, right: Expression)``:  represents ``left + right``
- ``SubtractionOp(left: Expression, right: Expression)``:  represents ``left - right``
- ``MultiplicationOp(left: Expression, right: Expression)``:  represents ``left * right``
- ``DivisionOp(left: Expression, right: Expression)``:  represents ``left / right``
- ``ModuloOp(left: Expression, right: Expression)``:  represents ``left % right``
- ``ExponentOp(left: Expression, right: Expression)``:  represents ``left ^ right``
- ``UnaryMinusOp(expr: Expression)``:  represents ``-expr``

Logical:

- ``LogicalAndOp(left: Expression, right: Expression)``:  represents ``left && right``
- ``LogicalOrOp(left: Expression, right: Expression)``:  represents ``left || right``
- ``LogicalNotOp(expr: Expression)``:  represents ``!expr``

Comparison:

- ``EqualityOp(left: Expression, right: Expression)``: represents ``left == right``
- ``InequalityOp(left: Expression, right: Expression)``: represents ``left != right``
- ``GreaterThanOp(left: Expression, right: Expression)``: represents ``left > right``
- ``GreaterThanOrEqualOp(left: Expression, right: Expression)``: represents ``left >= right``
- ``LessThanOp(left: Expression, right: Expression)``: represents ``left < right``
- ``LessThanOrEqualOp(left: Expression, right: Expression)``: represents ``left <= right``

Bitwise:

- ``BitwiseAndOp(left: Expression, right: Expression)``: represents ``left & right``
- ``BitwiseOrOp(left: Expression, right: Expression)``: represents ``left | right``
- ``BitwiseShiftLeftOp(left: Expression, right: Expression)``: represents ``left << right``
- ``BitwiseShiftRightOp(left: Expression, right: Expression)``: represents ``left >> right``
- ``BitwiseNotOp(expr: Expression)``: represents ``~expr``

Other:

- ``TernaryOp(condition: Expression, true_expr: Expression, false_expr: Expression)``: Represents ``condition ? true_expr : false_expr``

Expressions
~~~~~~~~~~~

- ``LetOp(assignments: list[Assignment], body: Expression)``: let clause  ``let(assignments) body``
- ``EchoOp(arguments: list[Argument], body: Expression)``: echo clause  ``echo(arguments) body``
- ``AssertOp(arguments: list[Argument], body: Expression)``: assert clause  ``assert(arguments) body``
- ``FunctionLiteral(parameters: list[ParameterDeclaration], body: Expression)``: Anonymous function expression  ``function(parameters) body``
- ``PrimaryCall(left: Expression, arguments: list[Argument])``: Function calls  ``left(arguments)``
- ``PrimaryIndex(left: Expression, index: Expression)``: Array indexing ``left[index]``
- ``PrimaryMember(left: Expression, member: Identifier)``: Member access ``left.member``

List Comprehensions
~~~~~~~~~~~~~~~~~~~

- ``ListComprehension(elements: list[VectorElement])``: Vector/list literals ``[elements]``
- ``ListCompFor(assignments: list[Assignment], body: VectorElement)``: for loops in list comprehensions ``for(assignments) body``
- ``ListCompCFor(inits: list[Assignment], condition: Expression, incrs: list[Assignment], body: VectorElement)``: C-style for loops in list comprehensions ``for(inits; condition; incrs) body``
- ``ListCompIf(condition: Expression, true_expr: VectorElement)``: Conditional inclusion without else ``if(condition) true_expr``
- ``ListCompIfElse(condition: Expression, true_expr: VectorElement, false_expr: VectorElement)``: Conditional inclusion with else ``if(condition) true_expr else false_expr``
- ``ListCompLet(assignments: list[Assignment], body: VectorElement)``: let expressions in list comprehensions ``let(assignments) body``
- ``ListCompEach(body: VectorElement)``: each expressions (flattens nested lists) ``each body``

Module Instantiations
~~~~~~~~~~~~~~~~~~~~~

- ``ModularCall(name: Identifier, arguments: list[Argument], children: list[ModuleInstantiation])``: Module calls ``name(arguments) { children }``
- ``ModularFor(assignments: list[Assignment], body: ModuleInstantiation)``: for loops in module bodies ``for(assignments) body``
- ``ModularIntersectionFor(assignments: list[Assignment], body: ModuleInstantiation)``: intersection_for loops ``intersection_for(assignments) body``
- ``ModularLet(assignments: list[Assignment], children: list[ModuleInstantiation])``: let statements in module bodies ``let(assignments) { children }``
- ``ModularEcho(arguments: list[Argument], children: list[ModuleInstantiation])``: echo statements in module bodies ``echo(arguments) { children }``
- ``ModularAssert(arguments: list[Argument], children: list[ModuleInstantiation])``: assert statements in module bodies ``assert(arguments) { children }``
- ``ModularIf(condition: Expression, true_branch: ModuleInstantiation)``: if statements in module bodies, with no else ``if(condition) true_branch``
- ``ModularIfElse(condition: Expression, true_branch: ModuleInstantiation, false_branch: ModuleInstantiation)``: if/else statements in module bodies ``if(condition) true_branch else false_branch``
- ``ModularModifierShowOnly(child: ModuleInstantiation)``: Show-Only modifier ``!child``
- ``ModularModifierHighlight(child: ModuleInstantiation)``: Highlight modifier ``#child``
- ``ModularModifierBackground(child: ModuleInstantiation)``: Background modifier ``%child``
- ``ModularModifierDisable(child: ModuleInstantiation)``: Disabler modifier ``*child``

Declarations
~~~~~~~~~~~~

- ``ModuleDeclaration(name: Identifier, parameters: list[ParameterDeclaration], children: list[ModuleInstantiation | Assignment | FunctionDeclaration | ModuleDeclaration])``: Module definitions ``module name(parameters) { children }``
- ``FunctionDeclaration(name: Identifier, parameters: list[ParameterDeclaration], expr: Expression)``: Function definitions ``function name(parameters) = expr;``
- ``ParameterDeclaration(name: Identifier, default: Expression | None)``: Function/module parameter with optional default value  ``name=default`` or ``name``
- ``Assignment(name: Identifier, expr: Expression)``: Variable assignments ``name = expr;``

Statements
~~~~~~~~~~

- ``UseStatement(filepath: StringLiteral)``: Represents ``use <filepath>``
- ``IncludeStatement(filepath: StringLiteral)``: Represents ``include <filepath>``
- ``PositionalArgument(expr: Expression)``: Function call positional arguments ``expr``
- ``NamedArgument(name: Identifier, expr: Expression)``: Function call named arguments ``name=expr``

Comments
~~~~~~~~

- ``CommentLine(text: str)``: Single-line comments ``// str``
- ``CommentSpan(text: str)``: Multi-line comments ``/* str */``

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

``getASTfromString(code: str, include_comments: bool = False, origin: str = "<string>")``
    Parse OpenSCAD code from a string and return its AST.

    :param code: The OpenSCAD source code to be parsed
    :param include_comments: If True, include comment nodes in the AST (default: False)
    :param origin: Origin identifier used in source position tracking (default: "<string>")
    :returns: AST node or list of AST nodes (for top-level statements)
    :rtype: ASTNode | list[ASTNode] | None

``getASTfromFile(file: str, include_comments: bool = False, process_includes: bool = True)``
    Parse an OpenSCAD source file and return its AST. Includes automatic caching
    that invalidates when the file's modification timestamp changes.

    :param file: The OpenSCAD source file to be parsed
    :param include_comments: If True, include comments in the AST (default: False)
    :param process_includes: If True, process include statements and replace with file contents (default: True).
        When False, the AST will contain IncludeStatement nodes where includes appear.
    :returns: List of AST nodes (for top-level statements)
    :rtype: list[ASTNode] | None
    :raises FileNotFoundError: If the specified file does not exist
    :raises Exception: If there is an error while reading the file

    **Note:** When ``process_includes=True`` (default), the AST will NOT contain ``IncludeStatement`` nodes
    because includes are processed before parsing. When ``process_includes=False``, ``IncludeStatement``
    nodes will appear in the AST where ``include <file>`` statements exist in the source code.
    
    Unlike ``include`` statements, ``use <file>`` statements are ALWAYS parsed into ``UseStatement``
    AST nodes regardless of the ``process_includes`` setting, since ``use`` only affects runtime
    lookup, not source inclusion.

``getASTfromLibraryFile(currfile: str, libfile: str, include_comments: bool = False, process_includes: bool = True)``
    Find and parse an OpenSCAD library file using OpenSCAD's search path rules.
    Searches in: current file directory, OPENSCADPATH, and platform default paths.

    :param currfile: Full path to the current OpenSCAD file (can be empty string)
    :param libfile: Partial or full path to the library file to find
    :param include_comments: If True, include comments in the AST (default: False)
    :param process_includes: If True, process include statements (default: True).
        When False, the AST will contain IncludeStatement nodes where includes appear.
    :returns: Tuple of (AST nodes list, absolute file path). The AST list is None if empty or not valid.
    :rtype: tuple[list[ASTNode] | None, str]
    :raises FileNotFoundError: If the library file cannot be found
    :raises Exception: If there is an error while reading or parsing the file

    **Note:** The ``process_includes`` parameter affects the AST structure (see ``getASTfromFile`` documentation).

``parse_ast(parser, code, file="", source_map=None)``
    Parse OpenSCAD code and generate an AST (lower-level API).

    :param parser: Arpeggio parser instance from getOpenSCADParser()
    :param code: OpenSCAD code string to parse
    :param file: Optional file path for source location tracking
    :param source_map: Optional ``SourceMap`` for multi-origin position tracking
    :returns: AST node or list of AST nodes (for top-level statements)

``clear_ast_cache()``
    Clear the in-memory AST cache, forcing all subsequent calls to
    ``getASTfromFile()`` to re-parse files.

    This function removes all cached AST trees from memory.

``build_scopes(ast: list[ASTNode]) -> Scope``
    Build a scope tree over an AST and attach a ``scope`` attribute to every node.

    :param ast: A list of top-level AST nodes (as returned by the ``getAST*`` functions)
    :returns: The root ``Scope`` object

``Scope``
    Represents a lexical scope with three independent namespaces (variables, functions,
    modules), mirroring OpenSCAD's scoping rules.

    - ``scope.lookup_variable(name)`` — search this scope and its parents
    - ``scope.lookup_function(name)`` — search this scope and its parents
    - ``scope.lookup_module(name)`` — search this scope and its parents
    - ``scope.parent`` — the enclosing scope (``None`` for root)

``to_openscad(nodes: list[ASTNode], indent_width: int = 4)``
    Convert a list of AST nodes to formatted OpenSCAD source code.

    :param nodes: Top-level AST nodes as returned by the ``getAST*`` functions.
    :param indent_width: Spaces per indentation level (default: 4).
    :returns: Formatted OpenSCAD source as a string.

Serialization Functions
~~~~~~~~~~~~~~~~~~~~~~~

``ast_to_dict(ast: ASTNode | Sequence[ASTNode] | None, include_position: bool = True)``
    Convert an AST to a Python dictionary (JSON-serializable).

    :param ast: An AST node, sequence of AST nodes, or None
    :param include_position: If True, include source position information (default: True)
    :returns: A dictionary representation of the AST, a list of dictionaries, or None
    :rtype: dict[str, Any] | list[dict[str, Any]] | None

``ast_to_json(ast: ASTNode | Sequence[ASTNode] | None, include_position: bool = True, indent: int | None = 2)``
    Serialize an AST to a JSON string.

    :param ast: An AST node, sequence of AST nodes, or None
    :param include_position: If True, include source position information (default: True)
    :param indent: Indentation level for pretty-printing. Use None for compact output (default: 2)
    :returns: A JSON string representation of the AST
    :rtype: str

``ast_from_dict(data: dict[str, Any] | list[dict[str, Any]] | None)``
    Reconstruct an AST from a Python dictionary.

    :param data: A dictionary, list of dictionaries, or None (as returned by ast_to_dict)
    :returns: An AST node, list of AST nodes, or None
    :rtype: ASTNode | list[ASTNode] | None
    :raises ValueError: If the data contains an unknown node type or is malformed

``ast_from_json(json_str: str)``
    Deserialize an AST from a JSON string.

    :param json_str: A JSON string (as returned by ast_to_json)
    :returns: An AST node, list of AST nodes, or None
    :rtype: ASTNode | list[ASTNode] | None
    :raises ValueError: If the JSON contains an unknown node type or is malformed
    :raises json.JSONDecodeError: If the string is not valid JSON

``ast_to_yaml(ast: ASTNode | Sequence[ASTNode] | None, include_position: bool = True)``
    Serialize an AST to a YAML string.

    Requires PyYAML to be installed: ``pip install openscad_parser[yaml]``

    :param ast: An AST node, sequence of AST nodes, or None
    :param include_position: If True, include source position information (default: True)
    :returns: A YAML string representation of the AST
    :rtype: str
    :raises ImportError: If PyYAML is not installed

``ast_from_yaml(yaml_str: str)``
    Deserialize an AST from a YAML string.

    Requires PyYAML to be installed: ``pip install openscad_parser[yaml]``

    :param yaml_str: A YAML string (as returned by ast_to_yaml)
    :returns: An AST node, list of AST nodes, or None
    :rtype: ASTNode | list[ASTNode] | None
    :raises ImportError: If PyYAML is not installed
    :raises ValueError: If the YAML contains an unknown node type or is malformed

AST Node Classes
~~~~~~~~~~~~~~~~

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

    from openscad_parser.ast import getASTfromFile, Position

    ast = getASTfromFile("example.scad")
    assignment = ast[0]

    position = assignment.position
    print(position.origin)        # "example.scad" (origin identifier)
    print(position.line)          # 1 (1-indexed line number)
    print(position.column)        # 1 (1-indexed column number)
    print(position.start_offset)  # 0 (0-based byte offset of token start within origin)
    print(position.end_offset)    # N (0-based exclusive byte offset of token end)

The ``Position`` dataclass carries both line/column coordinates and byte offsets relative
to the origin's content. For single-file parses these equal file byte offsets; for
multi-origin parses (e.g. after include expansion) they are relative to each included file.

Serialization
-------------

AST trees can be serialized to JSON or YAML formats and deserialized back to AST nodes. This is useful for caching, storage, or transferring AST data between processes.

JSON Serialization
~~~~~~~~~~~~~~~~~~

Serialize an AST to JSON::

    from openscad_parser.ast import getASTfromString, ast_to_json, ast_from_json

    # Parse code to AST
    ast = getASTfromString("cube(10);")

    # Serialize to JSON string
    json_str = ast_to_json(ast, include_position=True, indent=2)

    # Deserialize back to AST
    ast_restored = ast_from_json(json_str)

The ``ast_to_json()`` function accepts:
- ``ast``: An AST node, sequence of AST nodes, or None
- ``include_position``: If True, include source position information (default: True)
- ``indent``: Indentation level for pretty-printing. Use None for compact output (default: 2)

Dictionary Serialization
~~~~~~~~~~~~~~~~~~~~~~~~~

You can also work with Python dictionaries directly::

    from openscad_parser.ast import getASTfromString, ast_to_dict, ast_from_dict

    ast = getASTfromString("x = 42;")

    # Convert to dictionary
    data = ast_to_dict(ast, include_position=True)

    # Convert back to AST
    ast_restored = ast_from_dict(data)

YAML Serialization
~~~~~~~~~~~~~~~~~~

For YAML serialization, you need to install PyYAML::

    pip install openscad_parser[yaml]

Then serialize to YAML::

    from openscad_parser.ast import getASTfromString, ast_to_yaml, ast_from_yaml

    ast = getASTfromString("cube(10);")

    # Serialize to YAML string
    yaml_str = ast_to_yaml(ast, include_position=True)

    # Deserialize back to AST
    ast_restored = ast_from_yaml(yaml_str)

The ``ast_to_yaml()`` function accepts:
- ``ast``: An AST node, sequence of AST nodes, or None
- ``include_position``: If True, include source position information (default: True)

Serialization Functions
~~~~~~~~~~~~~~~~~~~~~~~

All serialization functions can be imported directly from ``openscad_parser.ast`` (recommended)::

    from openscad_parser.ast import (
        ast_to_dict,
        ast_to_json,
        ast_to_yaml,
        ast_from_dict,
        ast_from_json,
        ast_from_yaml,
    )

They are also available from ``openscad_parser.ast.serialization``::

    from openscad_parser.ast.serialization import (
        ast_to_dict,
        ast_to_json,
        ast_to_yaml,
        ast_from_dict,
        ast_from_json,
        ast_from_yaml,
    )

Pretty-Printing
---------------

The ``to_openscad()`` function converts an AST back to formatted OpenSCAD source code::

    from openscad_parser.ast import getASTfromString, to_openscad

    code = "module box(w,h){cube([w,h,1]);}"
    ast = getASTfromString(code)

    formatted = to_openscad(ast)
    # module box(w, h) {
    #     cube([w, h, 1.0]);
    # }
    print(formatted)

The pretty-printer normalises whitespace and indentation while preserving the logical
structure of the code. It supports all AST node types including modules, functions,
control structures, modifiers, list comprehensions, and comments.

``to_openscad(nodes, indent_width=4)``
    Convert a list of AST nodes to formatted OpenSCAD source.

    :param nodes: Top-level AST nodes (as returned by ``getAST*`` functions).
    :param indent_width: Spaces per indentation level (default: 4).
    :returns: Formatted OpenSCAD source code as a string.

    - Blank lines are inserted before and after module/function declarations.
    - Single-child module instantiations are formatted inline; multiple children use a block.
    - Comments are preserved when the AST was parsed with ``include_comments=True``.

Controlling indentation::

    from openscad_parser.ast import getASTfromString, to_openscad

    ast = getASTfromString("module m() { cube(1); }")
    print(to_openscad(ast, indent_width=2))
    # module m() {
    #   cube(1.0);
    # }

Command-Line Interface
-----------------------

The ``openscad-parser`` CLI is installed alongside the package::

    pip install openscad-parser

Usage::

    openscad-parser [OPTIONS] [FILE]

Read from a file or ``-`` for stdin. Default output is JSON.

**Options:**

``--json``
    Output AST as JSON (default).

``--yaml``
    Output AST as YAML (requires ``pip install openscad_parser[yaml]``).

``--format``
    Output reformatted OpenSCAD source code.

``--indent N``
    Indentation width in spaces (default: 4). Applies to ``--format`` and ``--json``.

``--include-comments``
    Include comment nodes in the output.

``--no-includes``
    Do not expand ``include <...>`` statements; keep ``IncludeStatement`` nodes instead.

**Examples:**

Dump AST as JSON::

    openscad-parser model.scad
    openscad-parser - < model.scad         # stdin

Reformat OpenSCAD source::

    openscad-parser --format model.scad
    openscad-parser --format --indent 2 model.scad

Output YAML::

    openscad-parser --yaml model.scad

Include comments in the AST::

    openscad-parser --include-comments --json model.scad

Error Handling
--------------

The parser will raise ``SyntaxError`` exceptions for invalid OpenSCAD syntax::

    from openscad_parser.ast import getASTfromString

    try:
        code = "x = ;"  # Invalid syntax
        ast = getASTfromString(code)
    except SyntaxError as e:
        print(f"Parse error: {e}")

File operations will raise ``FileNotFoundError`` for missing files::

    from openscad_parser.ast import getASTfromFile, getASTfromLibraryFile

    try:
        ast = getASTfromFile("nonexistent.scad")
    except FileNotFoundError as e:
        print(f"File not found: {e}")

    try:
        ast, path = getASTfromLibraryFile("main.scad", "missing_lib.scad")
    except FileNotFoundError as e:
        print(f"Library file not found: {e}")

Advanced Usage
--------------

File Caching
~~~~~~~~~~~~

The ``getASTfromFile()`` function automatically caches parsed ASTs in memory::

    from openscad_parser.ast import getASTfromFile

    # First call parses and caches
    ast1 = getASTfromFile("model.scad")

    # Second call returns cached AST (same object)
    ast2 = getASTfromFile("model.scad")
    assert ast1 is ast2  # True - same cached object

    # After file modification, cache is invalidated and file is re-parsed
    # (modify model.scad here)
    ast3 = getASTfromFile("model.scad")
    assert ast1 is not ast3  # True - new parse after modification

Cache entries are automatically invalidated when a file's modification timestamp changes. To manually clear the cache::

    from openscad_parser.ast import clear_ast_cache

    clear_ast_cache()  # Clear all cached ASTs

Reusing Parser Instances
~~~~~~~~~~~~~~~~~~~~~~~~

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

    from openscad_parser.ast import getASTfromString
    
    code = "x = 10; y = 20;"
    ast = getASTfromString(code)
    for node in ast:
        visit_node(node)

Scope Tracking
--------------

The parser can build a scope tree over the AST, resolving variable, function, and module
names according to OpenSCAD's three-namespace scoping rules::

    from openscad_parser.ast import getASTfromString, build_scopes

    ast = getASTfromString("""
        x = 10;
        module box(size = x) { cube(size); }
        box();
    """)

    root_scope = build_scopes(ast)

    # Look up names in the root scope
    print(root_scope.lookup_variable("x"))   # Assignment node
    print(root_scope.lookup_module("box"))   # ModuleDeclaration node

    # Each AST node has a .scope attribute pointing to its enclosing scope
    box_decl = ast[1]
    cube_call = box_decl.children[0]
    print(cube_call.scope.lookup_variable("size"))  # ParameterDeclaration node

``build_scopes(ast)`` returns the root ``Scope`` object and attaches a ``scope`` attribute
to every node in the tree. Scopes form a parent chain so lookups fall through to enclosing
scopes automatically. Declarations (variables, functions, modules) inside a block are
hoisted to the top of that block's scope before child nodes are visited.

Testing
-------

The project includes a comprehensive test suite. Run tests with::

    uv run pytest tests/

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

