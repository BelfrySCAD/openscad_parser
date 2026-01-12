"""Tests for AST convenience functions: getASTfromString, getASTfromFile, getASTfromLibraryFile."""

import os
import sys
import time
import tempfile
import pytest
from openscad_parser.ast import (
    getASTfromString,
    getASTfromFile,
    getASTfromLibraryFile,
    findLibraryFile,
    clear_ast_cache,
    Assignment,
    ModuleDeclaration,
    FunctionDeclaration,
    Identifier,
    NumberLiteral,
    AdditionOp,
    ModularCall,
)


class TestGetASTfromString:
    """Test getASTfromString() function."""

    def test_simple_assignment(self):
        """Test parsing a simple assignment from string."""
        code = "x = 42;"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].name, Identifier)
        assert ast[0].name.name == "x"
        assert isinstance(ast[0].expr, NumberLiteral)
        assert ast[0].expr.val == 42

    def test_complex_expression(self):
        """Test parsing a complex expression from string."""
        code = "result = 10 + 5;"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, AdditionOp)
        assert isinstance(ast[0].expr.left, NumberLiteral)
        assert ast[0].expr.left.val == 10
        assert isinstance(ast[0].expr.right, NumberLiteral)
        assert ast[0].expr.right.val == 5

    def test_module_declaration(self):
        """Test parsing a module declaration from string."""
        code = "module test() { cube(10); }"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], ModuleDeclaration)
        assert isinstance(ast[0].name, Identifier)
        assert ast[0].name.name == "test"

    def test_function_declaration(self):
        """Test parsing a function declaration from string."""
        code = "function add(x, y) = x + y;"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], FunctionDeclaration)
        assert isinstance(ast[0].name, Identifier)
        assert ast[0].name.name == "add"

    def test_empty_code(self):
        """Test parsing empty code."""
        code = ""
        ast = getASTfromString(code)
        
        # Empty code may return None or empty list depending on implementation
        assert ast is None or (isinstance(ast, list) and len(ast) == 0)

    def test_multiple_statements(self):
        """Test parsing multiple statements from string."""
        code = "x = 1; y = 2; z = 3;"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 3
        for i, assignment in enumerate(ast):
            assert isinstance(assignment, Assignment)
            assert assignment.name.name == ["x", "y", "z"][i]


class TestGetASTfromFile:
    """Test getASTfromFile() function."""

    def test_parse_file(self):
        """Test parsing a file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            test_file = f.name
            f.write("x = 42;")
        
        try:
            ast = getASTfromFile(test_file)
            
            assert ast is not None
            assert isinstance(ast, list)
            assert len(ast) == 1
            assert isinstance(ast[0], Assignment)
            assert ast[0].name.name == "x"
        finally:
            os.unlink(test_file)

    def test_file_caching(self):
        """Test that file caching works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            test_file = f.name
            f.write("x = 42;")
        
        try:
            # First call - should parse and cache
            ast1 = getASTfromFile(test_file)
            
            # Second call - should return cached version
            ast2 = getASTfromFile(test_file)
            
            # Should be the same object (cached)
            assert ast1 is ast2
        finally:
            os.unlink(test_file)

    def test_cache_invalidation_on_modification(self):
        """Test that cache is invalidated when file is modified."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            test_file = f.name
            f.write("x = 42;")
        
        try:
            # First call - should parse and cache
            ast1 = getASTfromFile(test_file)
            
            # Modify file
            time.sleep(0.1)  # Ensure mtime changes
            with open(test_file, 'w') as f:
                f.write("y = 100;")
            
            # Third call - should re-parse due to modification
            ast2 = getASTfromFile(test_file)
            
            # Should be different objects
            assert ast1 is not None
            assert ast2 is not None
            assert ast1 is not ast2
            assert isinstance(ast1[0], Assignment)
            assert ast1[0].name.name == "x"
            assert isinstance(ast2[0], Assignment)
            assert ast2[0].name.name == "y"
        finally:
            os.unlink(test_file)

    def test_file_not_found(self):
        """Test that FileNotFoundError is raised for non-existent files."""
        with pytest.raises(FileNotFoundError):
            getASTfromFile("nonexistent_file.scad")

    def test_multiple_files_cached_independently(self):
        """Test that multiple files are cached independently."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f1:
            file1 = f1.name
            f1.write("x = 1;")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f2:
            file2 = f2.name
            f2.write("y = 2;")
        
        try:
            ast1a = getASTfromFile(file1)
            ast2a = getASTfromFile(file2)
            
            ast1b = getASTfromFile(file1)
            ast2b = getASTfromFile(file2)
            
            # Each file should return its own cached version
            assert ast1a is ast1b
            assert ast2a is ast2b
            assert ast1a is not ast2a
        finally:
            os.unlink(file1)
            os.unlink(file2)

    def test_clear_cache(self):
        """Test that clear_ast_cache() clears the cache."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            test_file = f.name
            f.write("x = 42;")
        
        try:
            # Parse and cache
            ast1 = getASTfromFile(test_file)
            
            # Clear cache
            clear_ast_cache()
            
            # Parse again - should create new AST (not cached)
            ast2 = getASTfromFile(test_file)
            
            # Should be different objects (cache was cleared)
            assert ast1 is not ast2
        finally:
            os.unlink(test_file)


class TestFindLibraryFile:
    """Test _find_library_file() helper function."""

    def test_find_in_current_file_directory(self):
        """Test finding library file in current file's directory."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        # Create library file in same directory
        lib_dir = os.path.dirname(current_file)
        lib_file = os.path.join(lib_dir, "library.scad")
        with open(lib_file, 'w') as f:
            f.write("cube(10);")
        
        try:
            found = findLibraryFile(current_file, "library.scad")
            assert found == lib_file
        finally:
            os.unlink(current_file)
            os.unlink(lib_file)

    def test_find_with_nested_path(self):
        """Test finding library file with nested path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        # Create nested library structure
        lib_dir = os.path.dirname(current_file)
        utils_dir = os.path.join(lib_dir, "utils")
        os.makedirs(utils_dir, exist_ok=True)
        lib_file = os.path.join(utils_dir, "math.scad")
        with open(lib_file, 'w') as f:
            f.write("function add(x, y) = x + y;")
        
        try:
            # Debug: check if function is in global scope and try both names
            found = None
            if "findLibraryFile" in globals():
                found = findLibraryFile(current_file, "utils/math.scad")
            elif "_find_library_file" in globals():
                found = findLibraryFile(current_file, "utils/math.scad")
            else:
                # Try importing from src if available
                try:
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
                    found = findLibraryFile(current_file, "utils/math.scad")
                except Exception as e:
                    print("Could not import findLibraryFile:", e)
                    raise

            # Debug output
            print("Expected lib_file:", lib_file)
            print("Found file:      ", found)
            assert found == lib_file
        finally:
            os.unlink(current_file)
            os.unlink(lib_file)
            os.rmdir(utils_dir)
    def test_not_found_returns_none(self):
        """Test that None is returned when file is not found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        try:
            found = findLibraryFile(current_file, "nonexistent.scad")
            assert found is None
        finally:
            os.unlink(current_file)

    def test_empty_current_file(self):
        """Test finding library file without current file context."""
        # This should search in OPENSCADPATH and platform defaults
        # We can't easily test platform defaults, but we can verify it doesn't crash
        found = findLibraryFile("", "nonexistent.scad")
        assert found is None  # Should return None if not found


class TestGetASTfromLibraryFile:
    """Test getASTfromLibraryFile() function."""

    def test_find_and_parse_library_file(self):
        """Test finding and parsing a library file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        # Create library file in same directory
        lib_dir = os.path.dirname(current_file)
        lib_file = os.path.join(lib_dir, "library.scad")
        with open(lib_file, 'w') as f:
            f.write("cube(10);")
        
        try:
            ast, path = getASTfromLibraryFile(current_file, "library.scad")
            
            assert ast is not None
            assert isinstance(ast, list)
            assert len(ast) >= 1
            assert isinstance(ast[0], ModularCall)
            assert ast[0].name.name == "cube"
            assert path == os.path.abspath(lib_file)
        finally:
            os.unlink(current_file)
            os.unlink(lib_file)

    def test_find_and_parse_nested_library_file(self):
        """Test finding and parsing a nested library file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        # Create nested library structure
        lib_dir = os.path.dirname(current_file)
        utils_dir = os.path.join(lib_dir, "utils")
        os.makedirs(utils_dir, exist_ok=True)
        lib_file = os.path.join(utils_dir, "math.scad")
        with open(lib_file, 'w') as f:
            f.write("function add(x, y) = x + y;")
        
        try:
            ast, path = getASTfromLibraryFile(current_file, "utils/math.scad")
            
            assert ast is not None
            assert isinstance(ast, list)
            assert len(ast) == 1
            assert isinstance(ast[0], FunctionDeclaration)
            assert ast[0].name.name == "add"
            assert path == os.path.abspath(lib_file)
        finally:
            os.unlink(current_file)
            os.unlink(lib_file)
            os.rmdir(utils_dir)

    def test_library_file_not_found(self):
        """Test that FileNotFoundError is raised when library file is not found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        try:
            with pytest.raises(FileNotFoundError) as exc_info:
                getASTfromLibraryFile(current_file, "nonexistent.scad")
            
            assert "not found in search paths" in str(exc_info.value)
        finally:
            os.unlink(current_file)

    def test_library_file_caching(self):
        """Test that library files are cached via getASTfromFile."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            current_file = f.name
            f.write("// main file")
        
        # Create library file
        lib_dir = os.path.dirname(current_file)
        lib_file = os.path.join(lib_dir, "library.scad")
        with open(lib_file, 'w') as f:
            f.write("cube(10);")
        
        try:
            # First call - should parse and cache
            ast1, path1 = getASTfromLibraryFile(current_file, "library.scad")
            
            # Second call - should return cached version
            ast2, path2 = getASTfromLibraryFile(current_file, "library.scad")
            
            # Should be the same object (cached)
            assert ast1 is ast2
            # Paths should be the same
            assert path1 == path2
            assert path1 == os.path.abspath(lib_file)
        finally:
            os.unlink(current_file)
            os.unlink(lib_file)

    def test_without_current_file(self):
        """Test finding library file without current file context."""
        # This will search in OPENSCADPATH and platform defaults
        # We can't easily test without setting up those paths, so we just verify
        # it raises FileNotFoundError for a non-existent file
        with pytest.raises(FileNotFoundError):
            getASTfromLibraryFile("", "nonexistent_library.scad")


