import os
import platform
from typing import Optional
from arpeggio import NoMatch
from openscad_parser import getOpenSCADParser

# Import all AST nodes from nodes
from .nodes import (
    ASTNode,
    CommentLine,
    CommentSpan,
    Expression,
    Primary,
    Identifier,
    StringLiteral,
    NumberLiteral,
    BooleanLiteral,
    UndefinedLiteral,
    ParameterDeclaration,
    Argument,
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
    VectorElement,
    ListCompLet,
    ListCompEach,
    ListCompFor,
    ListCompCStyleFor,
    ListCompIf,
    ListCompIfElse,
    ListComprehension,
    ModuleInstantiation,
    ModularCall,
    ModularFor,
    ModularCLikeFor,
    ModularIntersectionFor,
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

# Import ASTBuilderVisitor and Position
from .builder import ASTBuilderVisitor, Position


# --- AST convenience functions ---

def findLibraryFile(currfile: str, libfile: str) -> Optional[str]:
    """Find a library file using OpenSCAD's search path rules.
    
    Searches for the library file in the following order:
    1. Directory of the current file (if currfile is provided)
    2. Directories specified in OPENSCADPATH environment variable
    3. Platform-specific default library directories
    
    Args:
        currfile: Full path to the current OpenSCAD file (can be empty string)
        libfile: Partial or full path to the library file to find
        
    Returns:
        Full path to the found library file, or None if not found
    """
    dirs = []
    
    # Add directory of current file if provided
    if currfile:
        dirs.append(os.path.dirname(os.path.abspath(currfile)))
    
    # Determine path separator and default path based on platform
    pathsep = ":"
    dflt_path = ""
    system = platform.system()
    
    if system == "Windows":
        dflt_path = os.path.join(os.path.expanduser("~"), "Documents", "OpenSCAD", "libraries")
        pathsep = ";"
    elif system == "Darwin":
        dflt_path = os.path.expanduser("~/Documents/OpenSCAD/libraries")
    elif system == "Linux":
        dflt_path = os.path.expanduser("~/.local/share/OpenSCAD/libraries")
    
    # Get OPENSCADPATH from environment or use default
    env = os.getenv("OPENSCADPATH", dflt_path)
    if env:
        for path in env.split(pathsep):
            expanded_path = os.path.expandvars(path)
            if expanded_path:
                dirs.append(expanded_path)
    
    # Search for the file in each directory
    for d in dirs:
        test_file = os.path.join(d, libfile)
        if os.path.isfile(test_file):
            return test_file
    
    return None


# Alias for backward compatibility (test_ast_convenience.py imports _find_library_file)
_find_library_file = findLibraryFile


def parse_ast(parser, code, file="") -> list[ASTNode] | None:
    """Parse code and return AST nodes using ASTBuilderVisitor.
    
    This is the main public API for converting OpenSCAD code to an AST.
    
    Args:
        parser: An Arpeggio parser instance (from getOpenSCADParser())
        code: The OpenSCAD code string to parse
        file: Optional file path for source location tracking
        
    Returns:
        The root AST node (or list of AST nodes for the root level)
    """
    try:
        parse_tree = parser.parse(code)
    except NoMatch as e:
        position = e.position
        print(f"Syntax error at line {position.line}, column {position.column}:")
        return None
    else:
        visitor = ASTBuilderVisitor(parser, file=file)
        return visitor.visit_parse_tree(parse_tree)


def getASTfromString(code: str, include_comments: bool = False) -> ASTNode | list[ASTNode] | None:
    """
    Parse OpenSCAD source code from a string and return its abstract syntax tree (AST).

    This function creates a new OpenSCAD parser instance, parses the provided code string,
    and returns the resulting AST (or list of AST nodes) for further analysis or processing.

    Args:
        code (str): The OpenSCAD source code to be parsed.
        include_comments (bool): If True, include comments in the AST (default: False).

    Returns:
        ASTNode | list[ASTNode] | None: The AST representation of the OpenSCAD source code.
            Returns None if the code is empty or does not contain valid statements.

    Example:
        ast = getASTfromString("cube([1,2,3]);")
        ast_with_comments = getASTfromString("cube([1,2,3]); // comment", include_comments=True)
    """
    parser = getOpenSCADParser(reduce_tree=False, include_comments=include_comments)
    ast = parse_ast(parser, code)
    return ast


# Module-level cache for AST trees
# Key: tuple of (absolute file path (str), include_comments (bool))
# Value: tuple of (AST nodes, modification timestamp)
_ast_cache: dict[tuple[str, bool], tuple[list[ASTNode] | None, float]] = {}


def clear_ast_cache():
    """Clear the in-memory AST cache.
    
    This function removes all cached AST trees, forcing all subsequent
    calls to getASTfromFile() to re-parse files.
    
    Example:
        clear_ast_cache()  # Clear all cached ASTs
    """
    _ast_cache.clear()


def getASTfromFile(file: str, include_comments: bool = False) -> list[ASTNode] | None:
    """
    Parse an OpenSCAD source file and return its corresponding abstract syntax tree (AST).

    This function reads the contents of the provided OpenSCAD file, parses it using the OpenSCAD parser,
    and returns the resulting AST (or list of AST nodes) for further analysis or processing.
    
    The function caches AST trees in memory. Cache entries are automatically invalidated
    if the file's modification timestamp changes, ensuring that updated files are re-parsed.

    Args:
        file (str): The OpenSCAD source file to be parsed.
        include_comments (bool): If True, include comments in the AST (default: False).

    Returns:
        list[ASTNode] | None: The AST representation of the OpenSCAD source file.
            Returns None if the file is empty or does not contain valid statements.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        Exception: If there is an error while reading the file.

    Example:
        ast = getASTfromFile("my_model.scad")
        ast_with_comments = getASTfromFile("my_model.scad", include_comments=True)
    """
    # Get absolute path for consistent cache keys
    file_path = os.path.abspath(file)
    
    # Check if file exists and get its modification time
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file} not found")
    
    current_mtime = os.path.getmtime(file_path)
    
    # Cache key includes file path and include_comments flag
    cache_key = (file_path, include_comments)
    
    # Check cache
    if cache_key in _ast_cache:
        cached_ast, cached_mtime = _ast_cache[cache_key]
        # If file hasn't been modified, return cached AST
        if cached_mtime == current_mtime:
            return cached_ast
        # Otherwise, invalidate the cache entry
        del _ast_cache[cache_key]
    
    # Parse the file
    try:
        with open(file_path, 'r') as f:
            code = f.read()
    except Exception as e:
        raise Exception(f"Error reading file {file}: {e}")
    
    parser = getOpenSCADParser(reduce_tree=False, include_comments=include_comments)
    ast = parse_ast(parser, code, file_path)
    
    # Cache the result with current modification time
    _ast_cache[cache_key] = (ast, current_mtime)
    
    return ast


def getASTfromLibraryFile(currfile: str, libfile: str, include_comments: bool = False) -> tuple[list[ASTNode] | None, str]:
    """
    Find and parse an OpenSCAD library file using OpenSCAD's search path rules,
    and return both the AST and absolute path to the file.

    This function searches for the library file in the following order:
    1. Directory of the current file (if currfile is provided)
    2. Directories specified in OPENSCADPATH environment variable
    3. Platform-specific default library directories:
       - Windows: ~/Documents/OpenSCAD/libraries
       - macOS: ~/Documents/OpenSCAD/libraries
       - Linux: ~/.local/share/OpenSCAD/libraries

    Once found, the file is parsed using getASTfromFile(), which includes
    caching support.

    Args:
        currfile: Full path to the current OpenSCAD file that wants to include/use
                  the library file. Can be empty string if not available.
        libfile: Partial or full path to the library file to find and parse.
                 This is typically the path specified in a 'use' or 'include' statement.
        include_comments (bool): If True, include comments in the AST (default: False).

    Returns:
        tuple[list[ASTNode] | None, str]: The AST representation of the library file
            and the absolute path of the file parsed. The list is None if empty or not valid.
    
    Raises:
        FileNotFoundError: If the library file cannot be found in any search path.
        Exception: If there is an error while reading or parsing the file.

    Example:
        # From a file at /path/to/main.scad that includes "utils/math.scad"
        ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad")
        
        # Or without current file context
        ast, path = getASTfromLibraryFile("", "MCAD/boxes.scad")
        
        # With comments
        ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad", include_comments=True)
    """
    found_file = findLibraryFile(currfile, libfile)

    if found_file is None:
        raise FileNotFoundError(
            f"Library file '{libfile}' not found in search paths. "
            f"Searched in: current file directory, OPENSCADPATH, and platform default paths."
        )

    # Use getASTfromFile() which includes caching
    ast = getASTfromFile(found_file, include_comments=include_comments)
    return ast, os.path.abspath(found_file)

