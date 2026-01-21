import os
import platform
from typing import Optional
from arpeggio import NoMatch
from openscad_parser import getOpenSCADParser
from .source_map import SourceMap, process_includes as process_includes_func

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
    ListCompCFor,
    ListCompIf,
    ListCompIfElse,
    ListComprehension,
    ModuleInstantiation,
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

# Import ASTBuilderVisitor and Position
from .builder import ASTBuilderVisitor, Position

# Import serialization functions
from .serialization import (
    ast_to_dict,
    ast_to_json,
    ast_from_dict,
    ast_from_json,
    ast_to_yaml,
    ast_from_yaml,
)


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
    
    if system == "Windows":  # pragma: no cover
        dflt_path = os.path.join(os.path.expanduser("~"), "Documents", "OpenSCAD", "libraries")
        pathsep = ";"
    elif system == "Darwin":  # pragma: no cover
        dflt_path = os.path.expanduser("~/Documents/OpenSCAD/libraries")
    elif system == "Linux":  # pragma: no cover
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


def parse_ast(parser, code, file="", source_map=None) -> list[ASTNode] | None:
    """Parse code and return AST nodes using ASTBuilderVisitor.
    
    This is the main public API for converting OpenSCAD code to an AST.
    
    Args:
        parser: An Arpeggio parser instance (from getOpenSCADParser())
        code: The OpenSCAD code string to parse
        file: Optional file path for source location tracking (deprecated, use source_map)
        source_map: Optional SourceMap for tracking positions across multiple origins
        
    Returns:
        The root AST node (or list of AST nodes for the root level)
    """
    try:
        parse_tree = parser.parse(code)
    except NoMatch as e:
        # Get character position from the exception - Arpeggio's NoMatch.position is an integer
        char_pos = e.position if isinstance(e.position, int) else 0
        
        # Use source_map to get accurate error location if available
        if source_map is not None:
            location = source_map.get_location(char_pos)
            error_origin = location.origin
            error_line = location.line
            error_column = location.column
            # Get the source code from source_map
            combined_code = source_map.get_combined_string()
        else:
            error_origin = file if file else "<unknown>"
            # Calculate line and column from character position
            if char_pos < 0:
                char_pos = 0  # pragma: no cover
            if char_pos > len(code):
                char_pos = len(code)  # pragma: no cover
            text_before = code[:char_pos]
            error_line = text_before.count('\n') + 1
            last_newline = text_before.rfind('\n')
            error_column = char_pos - last_newline  # 1-indexed
            combined_code = code
        
        # Extract the line where the error occurs
        lines = combined_code.split('\n')
        if 1 <= error_line <= len(lines):
            error_line_code = lines[error_line - 1]
            # Print error message
            print(f"Syntax error in {error_origin} at line {error_line}, column {error_column}:")
            print(error_line_code)
            # Print caret under the error position
            # Calculate caret position (accounting for tab characters)
            caret_pos = error_column - 1
            if caret_pos < 0:
                caret_pos = 0  # pragma: no cover
            if caret_pos > len(error_line_code):
                caret_pos = len(error_line_code)  # pragma: no cover
            # Expand tabs for display - calculate caret position in expanded line
            expanded_caret_pos = len(error_line_code[:caret_pos].expandtabs())
            print(' ' * expanded_caret_pos + '^')
        else:
            # Fallback if we can't get the line
            print(f"Syntax error in {error_origin} at line {error_line}, column {error_column}:")
        return None
    else:
        visitor = ASTBuilderVisitor(parser, source_map=source_map, file=file)
        return visitor.visit_parse_tree(parse_tree)


def getASTfromString(code: str, include_comments: bool = False, origin: str = "<string>") -> ASTNode | list[ASTNode] | None:
    """
    Parse OpenSCAD source code from a string and return its abstract syntax tree (AST).

    This function creates a new OpenSCAD parser instance, parses the provided code string,
    and returns the resulting AST (or list of AST nodes) for further analysis or processing.

    Args:
        code (str): The OpenSCAD source code to be parsed.
        include_comments (bool): If True, include comments in the AST (default: False).
        origin (str): Origin identifier for source location tracking (default: "<string>").

    Returns:
        ASTNode | list[ASTNode] | None: The AST representation of the OpenSCAD source code.
            Returns None if the code is empty or does not contain valid statements.

    Example:
        ast = getASTfromString("cube([1,2,3]);")
        ast_with_comments = getASTfromString("cube([1,2,3]); // comment", include_comments=True)
    """
    # Create a source map for position tracking
    source_map = SourceMap()
    source_map.add_origin(origin, code)
    
    parser = getOpenSCADParser(reduce_tree=False, include_comments=include_comments)
    ast = parse_ast(parser, code, source_map=source_map)
    return ast


# Module-level cache for AST trees
# Key: tuple of (absolute file path (str), include_comments (bool), process_includes (bool))
# Value: tuple of (AST nodes, modification timestamp)
_ast_cache: dict[tuple[str, bool, bool], tuple[list[ASTNode] | None, float]] = {}


def clear_ast_cache():
    """Clear the in-memory AST cache.
    
    This function removes all cached AST trees, forcing all subsequent
    calls to getASTfromFile() to re-parse files.
    
    Example:
        clear_ast_cache()  # Clear all cached ASTs
    """
    _ast_cache.clear()


def getASTfromFile(file: str, include_comments: bool = False, process_includes: bool = True) -> list[ASTNode] | None:
    """
    Parse an OpenSCAD source file and return its corresponding abstract syntax tree (AST).

    This function reads the contents of the provided OpenSCAD file, processes include statements,
    parses it using the OpenSCAD parser, and returns the resulting AST (or list of AST nodes).

    The function caches AST trees in memory. Cache entries are automatically invalidated
    if the file's modification timestamp changes, ensuring that updated files are re-parsed.

    Important: The `process_includes` parameter affects the AST structure:
    
    - When `process_includes=True` (default): Include statements are processed before parsing,
      meaning the included file contents are inserted into the source code, and the AST will
      NOT contain `IncludeStatement` nodes. The AST represents the code as if all includes
      have been expanded.
    
    - When `process_includes=False`: Include statements are NOT processed, and the AST will
      contain `IncludeStatement` nodes wherever `include <file>` statements appear in the
      source code.
    
    Note: Unlike `include` statements, `use <file>` statements are ALWAYS parsed into
    `UseStatement` AST nodes, regardless of the `process_includes` setting. This is because
    `use` statements only affect module and function lookup at runtime, not source inclusion.

    Args:
        file (str): The OpenSCAD source file to be parsed.
        include_comments (bool): If True, include comments in the AST (default: False).
        process_includes (bool): If True, process include statements and replace with file contents (default: True).
            When False, the AST will contain IncludeStatement nodes where includes appear.

    Returns:
        list[ASTNode] | None: The AST representation of the OpenSCAD source file.
            Returns None if the file is empty or does not contain valid statements.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        Exception: If there is an error while reading the file.

    Example:
        ast = getASTfromFile("my_model.scad")
        ast_with_comments = getASTfromFile("my_model.scad", include_comments=True)
        # Get AST with IncludeStatement nodes instead of processing includes
        ast_with_include_nodes = getASTfromFile("my_model.scad", process_includes=False)
    """
    # Get absolute path for consistent cache keys
    file_path = os.path.abspath(file)
    
    # Check if file exists and get its modification time
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file} not found")
    
    current_mtime = os.path.getmtime(file_path)
    
    # Cache key includes file path, include_comments flag, and process_includes flag
    cache_key = (file_path, include_comments, process_includes)
    
    # Check cache
    if cache_key in _ast_cache:
        cached_ast, cached_mtime = _ast_cache[cache_key]
        # If file hasn't been modified, return cached AST
        if cached_mtime == current_mtime:
            return cached_ast
        # Otherwise, invalidate the cache entry
        del _ast_cache[cache_key]
    
    # Read the file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
    except Exception as e:
        raise Exception(f"Error reading file {file}: {e}")
    
    # Create source map and process includes if requested
    source_map = SourceMap()
    source_map.add_origin(file_path, code)
    
    if process_includes:
        try:
            source_map = process_includes_func(source_map, file_path)
        except FileNotFoundError as e:
            # Re-raise file not found errors as-is
            raise
        except Exception as e:  # pragma: no cover
            raise Exception(f"Error processing includes: {e}")
    
    # Get the combined string for parsing
    combined_code = source_map.get_combined_string()
    
    # Parse
    parser = getOpenSCADParser(reduce_tree=False, include_comments=include_comments)
    ast = parse_ast(parser, combined_code, source_map=source_map)
    
    # Cache the result with current modification time
    _ast_cache[cache_key] = (ast, current_mtime)
    
    return ast


def getASTfromLibraryFile(currfile: str, libfile: str, include_comments: bool = False, process_includes: bool = True) -> tuple[list[ASTNode] | None, str]:
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
    caching support and include processing.

    Important: The `process_includes` parameter affects the AST structure (see getASTfromFile
    documentation for details). When `process_includes=False`, the AST will contain
    `IncludeStatement` nodes; when `True`, includes are processed and no `IncludeStatement`
    nodes appear. Note that `use <file>` statements are always parsed into `UseStatement`
    AST nodes regardless of the `process_includes` setting.

    Args:
        currfile: Full path to the current OpenSCAD file that wants to include/use
                  the library file. Can be empty string if not available.
        libfile: Partial or full path to the library file to find and parse.
                 This is typically the path specified in a 'use' or 'include' statement.
        include_comments (bool): If True, include comments in the AST (default: False).
        process_includes (bool): If True, process include statements (default: True).
            When False, the AST will contain IncludeStatement nodes where includes appear.

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
        
        # Without processing includes (AST will contain IncludeStatement nodes)
        ast, path = getASTfromLibraryFile("/path/to/main.scad", "utils/math.scad", process_includes=False)
    """
    found_file = findLibraryFile(currfile, libfile)

    if found_file is None:
        raise FileNotFoundError(
            f"Library file '{libfile}' not found in search paths. "
            f"Searched in: current file directory, OPENSCADPATH, and platform default paths."
        )

    # Use getASTfromFile() which includes caching and include processing
    ast = getASTfromFile(found_file, include_comments=include_comments, process_includes=process_includes)
    return ast, os.path.abspath(found_file)

