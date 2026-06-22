import hashlib
import json
import os
import pickle
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
    CommentedExpr,
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

# Import scope classes
from .scope import Scope, build_scopes

# Import pretty-printer
from .pretty_print import to_openscad

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


# Module-level in-memory cache for per-file AST trees (no includes resolved)
# Key: tuple of (absolute file path (str), include_comments (bool))
# Value: tuple of (AST nodes, modification timestamp)
_ast_cache: dict[tuple[str, bool], tuple[list[ASTNode] | None, float]] = {}

# Resolved (includes-expanded) cache
# Key: tuple of (absolute file path (str), include_comments (bool), process_includes (bool))
# Value: tuple of (AST nodes, modification timestamp)
_resolved_cache: dict[tuple[str, bool, bool], tuple[list[ASTNode] | None, float]] = {}


def _get_disk_cache_dir() -> Optional[str]:
    """Get the disk cache directory, creating it if needed."""
    cache_dir = os.environ.get('OPENSCAD_PARSER_CACHE_DIR')
    if not cache_dir:
        home = os.path.expanduser('~')
        if platform.system() == 'Darwin':
            cache_dir = os.path.join(home, 'Library', 'Caches', 'openscad_parser')
        elif platform.system() == 'Windows':  # pragma: no cover
            cache_dir = os.path.join(os.environ.get('LOCALAPPDATA', home), 'openscad_parser', 'cache')
        else:
            cache_dir = os.path.join(home, '.cache', 'openscad_parser')
    try:
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir
    except OSError:  # pragma: no cover
        return None


def _disk_cache_path(file_path: str, include_comments: bool) -> Optional[str]:
    """Get the disk cache file path for a given source file."""
    cache_dir = _get_disk_cache_dir()
    if not cache_dir:
        return None  # pragma: no cover
    key = f"{file_path}:{include_comments}"
    h = hashlib.sha256(key.encode()).hexdigest()[:16]
    return os.path.join(cache_dir, f"{h}.pickle")


def _load_from_disk_cache(file_path: str, include_comments: bool, current_mtime: float) -> Optional[list[ASTNode]]:
    """Try to load a file's AST from disk cache."""
    cache_path = _disk_cache_path(file_path, include_comments)
    if not cache_path or not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, 'rb') as f:
            cached_mtime, ast = pickle.load(f)
        if cached_mtime == current_mtime:
            return ast
    except (OSError, pickle.UnpicklingError, ValueError, EOFError):
        pass
    return None


def _save_to_disk_cache(file_path: str, include_comments: bool, mtime: float, ast: list[ASTNode] | None):
    """Save a file's AST to disk cache and update the manifest."""
    cache_path = _disk_cache_path(file_path, include_comments)
    if not cache_path:
        return  # pragma: no cover
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump((mtime, ast), f, protocol=pickle.HIGHEST_PROTOCOL)
    except OSError:  # pragma: no cover
        return
    cache_fname = os.path.basename(cache_path)
    _manifest_update(cache_fname, file_path)
    _evict_stale_cache()


def _manifest_path() -> Optional[str]:
    """Get the path to the cache manifest file."""
    cache_dir = _get_disk_cache_dir()
    if not cache_dir:
        return None  # pragma: no cover
    return os.path.join(cache_dir, "manifest.json")


def _manifest_load() -> dict[str, str]:
    """Load the manifest: {cache_filename: source_file_path}."""
    path = _manifest_path()
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _manifest_save(manifest: dict[str, str]):
    """Save the manifest to disk."""
    path = _manifest_path()
    if not path:
        return  # pragma: no cover
    try:
        with open(path, 'w') as f:
            json.dump(manifest, f)
    except OSError:  # pragma: no cover
        pass


def _manifest_update(cache_fname: str, source_path: str):
    """Add or update an entry in the manifest."""
    manifest = _manifest_load()
    manifest[cache_fname] = source_path
    _manifest_save(manifest)


def _evict_stale_cache():
    """Remove cache entries whose source files no longer exist."""
    cache_dir = _get_disk_cache_dir()
    if not cache_dir:
        return  # pragma: no cover
    manifest = _manifest_load()
    if not manifest:
        return
    stale_keys = [
        fname for fname, source_path in manifest.items()
        if not os.path.exists(source_path)
    ]
    if not stale_keys:
        return
    for fname in stale_keys:
        cache_file = os.path.join(cache_dir, fname)
        try:
            os.remove(cache_file)
        except OSError:
            pass
        del manifest[fname]
    _manifest_save(manifest)


def clear_ast_cache():
    """Clear the in-memory AST cache.

    This function removes all cached AST trees, forcing all subsequent
    calls to getASTfromFile() to re-parse files.

    Example:
        clear_ast_cache()  # Clear all cached ASTs
    """
    _ast_cache.clear()
    _resolved_cache.clear()


def clear_disk_cache():
    """Clear the on-disk AST cache.

    This function removes all cached AST files from disk, forcing all subsequent
    calls to re-parse files from scratch.

    Example:
        clear_disk_cache()  # Remove all disk-cached ASTs
    """
    cache_dir = _get_disk_cache_dir()
    if cache_dir and os.path.isdir(cache_dir):
        for fname in os.listdir(cache_dir):
            if fname.endswith('.pickle') or fname == 'manifest.json':
                try:
                    os.remove(os.path.join(cache_dir, fname))
                except OSError:  # pragma: no cover
                    pass


def _parse_single_file(file_path: str, include_comments: bool = False) -> list[ASTNode] | None:
    """Parse a single file without resolving includes. Uses memory and disk cache.

    Returns the AST with IncludeStatement nodes intact (not expanded).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} not found")

    current_mtime = os.path.getmtime(file_path)
    cache_key = (file_path, include_comments)

    # Check in-memory cache
    if cache_key in _ast_cache:
        cached_ast, cached_mtime = _ast_cache[cache_key]
        if cached_mtime == current_mtime:
            return cached_ast

    # Check disk cache
    disk_result = _load_from_disk_cache(file_path, include_comments, current_mtime)
    if disk_result is not None:
        _ast_cache[cache_key] = (disk_result, current_mtime)
        return disk_result

    # Parse the file
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    source_map = SourceMap()
    source_map.add_origin(file_path, code)

    parser = getOpenSCADParser(reduce_tree=False, include_comments=include_comments)
    ast = parse_ast(parser, code, source_map=source_map)

    # Cache in memory and on disk
    _ast_cache[cache_key] = (ast, current_mtime)
    _save_to_disk_cache(file_path, include_comments, current_mtime, ast)

    return ast


def _resolve_includes(ast_nodes: list[ASTNode] | None, current_file: str,
                      include_comments: bool = False,
                      visited: set | None = None) -> list[ASTNode] | None:
    """Resolve IncludeStatement nodes by parsing and inlining referenced files."""
    if ast_nodes is None:
        return None
    if visited is None:
        visited = set()

    result = []
    for node in ast_nodes:
        if isinstance(node, IncludeStatement):
            filename = node.filepath.val
            lib_file = findLibraryFile(current_file, filename)
            if lib_file is None:
                raise FileNotFoundError(
                    f"Included file '{filename}' not found. "
                    f"Searched relative to: {current_file if current_file else 'current directory'}"
                )
            lib_file = os.path.abspath(lib_file)
            if lib_file in visited:
                continue
            visited.add(lib_file)
            included_ast = _parse_single_file(lib_file, include_comments)
            included_ast = _resolve_includes(included_ast, lib_file, include_comments, visited)
            if included_ast:
                result.extend(included_ast)
        else:
            result.append(node)
    return result


def getASTfromFile(file: str, include_comments: bool = False, process_includes: bool = True) -> list[ASTNode] | None:
    """
    Parse an OpenSCAD source file and return its corresponding abstract syntax tree (AST).

    This function reads the contents of the provided OpenSCAD file, processes include statements,
    parses it using the OpenSCAD parser, and returns the resulting AST (or list of AST nodes).

    The function caches AST trees both in memory and on disk. Cache entries are automatically
    invalidated if a file's modification timestamp changes, ensuring updated files are re-parsed.
    Each included file is parsed independently and cached separately, so only changed files
    need re-parsing.

    Important: The `process_includes` parameter affects the AST structure:

    - When `process_includes=True` (default): Include statements are processed and resolved,
      meaning the included file's AST nodes are inlined, and the AST will NOT contain
      `IncludeStatement` nodes. The AST represents the code as if all includes have been expanded.

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
    file_path = os.path.abspath(file)

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file} not found")

    current_mtime = os.path.getmtime(file_path)

    # For process_includes=False, just parse the single file
    if not process_includes:
        return _parse_single_file(file_path, include_comments)

    # Check resolved cache (in-memory only since resolved ASTs depend on multiple files)
    resolved_key = (file_path, include_comments, True)
    if resolved_key in _resolved_cache:
        cached_ast, cached_mtime = _resolved_cache[resolved_key]
        if cached_mtime == current_mtime:
            return cached_ast

    # Parse the file independently (uses per-file cache)
    ast = _parse_single_file(file_path, include_comments)

    # Resolve all include statements recursively
    visited = {file_path}
    ast = _resolve_includes(ast, file_path, include_comments, visited)

    # Cache the resolved result
    _resolved_cache[resolved_key] = (ast, current_mtime)

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

