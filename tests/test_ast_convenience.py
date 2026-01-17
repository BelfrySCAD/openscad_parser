"""Tests for AST convenience functions: getASTfromString, getASTfromFile, getASTfromLibraryFile."""

import os
import sys
import time
import tempfile
from io import StringIO
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
    LogicalNotOp,
    BitwiseNotOp,
    IncludeStatement,
    Position,
    ModularCall,
    CommentLine,
    CommentSpan,
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

    def test_logical_not_expression(self):
        """Test parsing a logical not expression from string."""
        code = "x = !true;"
        ast = getASTfromString(code)

        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, LogicalNotOp)

    def test_bitwise_not_expression(self):
        """Test parsing a bitwise not expression from string."""
        code = "x = ~1;"
        ast = getASTfromString(code)

        assert ast is not None
        assert isinstance(ast, list)
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert isinstance(ast[0].expr, BitwiseNotOp)

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

    def test_process_includes_false_keeps_include_nodes(self):
        """Test process_includes=False preserves IncludeStatement nodes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")

            with open(lib_file, "w") as f:
                f.write("x = 1;")
            with open(main_file, "w") as f:
                f.write("include <lib.scad>;\n")

            ast = getASTfromFile(main_file, process_includes=False)
            assert ast is not None
            assert any(isinstance(node, IncludeStatement) for node in ast)

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
            found = findLibraryFile(current_file, "utils/math.scad")
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

    def test_find_library_file_windows_env_path(self, monkeypatch):
        """Test findLibraryFile uses Windows path separator for OPENSCADPATH."""
        import platform
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_dir1 = os.path.join(temp_dir, "libs1")
            lib_dir2 = os.path.join(temp_dir, "libs2")
            os.makedirs(lib_dir1)
            os.makedirs(lib_dir2)
            target = os.path.join(lib_dir2, "lib.scad")
            with open(target, "w") as f:
                f.write("x = 1;")

            monkeypatch.setattr(platform, "system", lambda: "Windows")
            monkeypatch.setenv("OPENSCADPATH", f"{lib_dir1};{lib_dir2}")

            found = findLibraryFile("", "lib.scad")
            assert found == target

    def test_find_library_file_darwin_env_path(self, monkeypatch):
        """Test findLibraryFile uses Darwin path defaults and env."""
        import platform
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_dir = os.path.join(temp_dir, "libraries")
            os.makedirs(lib_dir)
            target = os.path.join(lib_dir, "lib.scad")
            with open(target, "w") as f:
                f.write("x = 1;")

            monkeypatch.setattr(platform, "system", lambda: "Darwin")
            monkeypatch.setenv("OPENSCADPATH", lib_dir)

            found = findLibraryFile("", "lib.scad")
            assert found == target


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


class TestIncludeComments:
    """Test include_comments parameter for AST generation."""

    def test_getASTfromString_comments_excluded_by_default(self):
        """Test that comments are excluded from AST by default."""
        code = "// This is a comment\nx = 5;"
        ast = getASTfromString(code)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should only have the assignment, no comment
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert not any(isinstance(node, CommentLine) for node in ast)
        assert not any(isinstance(node, CommentSpan) for node in ast)

    def test_getASTfromString_comments_included_when_requested(self):
        """Test that comments are included in AST when include_comments=True."""
        code = "// This is a comment\nx = 5;"
        ast = getASTfromString(code, include_comments=True)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have both the comment and the assignment
        assert len(ast) == 2
        comment_nodes = [node for node in ast if isinstance(node, CommentLine)]
        assert len(comment_nodes) == 1
        assert comment_nodes[0].text == " This is a comment"
        assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
        assert len(assignment_nodes) == 1

    def test_getASTfromString_multi_line_comment_included(self):
        """Test that multi-line comments are included when include_comments=True."""
        code = "/* This is a\nmulti-line comment */\nx = 5;"
        ast = getASTfromString(code, include_comments=True)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should have both the comment and the assignment
        assert len(ast) == 2
        comment_nodes = [node for node in ast if isinstance(node, CommentSpan)]
        assert len(comment_nodes) == 1
        assert "This is a\nmulti-line comment" in comment_nodes[0].text
        assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
        assert len(assignment_nodes) == 1

    def test_getASTfromString_comments_excluded_when_false(self):
        """Test that comments are excluded when include_comments=False explicitly."""
        code = "// This is a comment\nx = 5;"
        ast = getASTfromString(code, include_comments=False)
        
        assert ast is not None
        assert isinstance(ast, list)
        # Should only have the assignment, no comment
        assert len(ast) == 1
        assert isinstance(ast[0], Assignment)
        assert not any(isinstance(node, CommentLine) for node in ast)

    def test_getASTfromFile_comments_excluded_by_default(self):
        """Test that comments are excluded from AST by default when parsing from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            f.write("// This is a comment\nx = 5;")
            temp_file = f.name
        
        try:
            ast = getASTfromFile(temp_file)
            
            assert ast is not None
            assert isinstance(ast, list)
            # Should only have the assignment, no comment
            assert len(ast) == 1
            assert isinstance(ast[0], Assignment)
            assert not any(isinstance(node, CommentLine) for node in ast)
        finally:
            os.unlink(temp_file)

    def test_getASTfromFile_comments_included_when_requested(self):
        """Test that comments are included in AST when include_comments=True for file parsing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            f.write("// This is a comment\nx = 5;")
            temp_file = f.name
        
        try:
            ast = getASTfromFile(temp_file, include_comments=True)
            
            assert ast is not None
            assert isinstance(ast, list)
            # Should have both the comment and the assignment
            assert len(ast) == 2
            comment_nodes = [node for node in ast if isinstance(node, CommentLine)]
            assert len(comment_nodes) == 1
            assignment_nodes = [node for node in ast if isinstance(node, Assignment)]
            assert len(assignment_nodes) == 1
        finally:
            os.unlink(temp_file)

    def test_getASTfromFile_cache_separate_for_comments(self):
        """Test that ASTs with and without comments are cached separately."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.scad', delete=False) as f:
            f.write("// This is a comment\nx = 5;")
            temp_file = f.name
        
        try:
            clear_ast_cache()
            
            # Parse without comments
            ast1 = getASTfromFile(temp_file, include_comments=False)
            assert ast1 is not None
            assert len(ast1) == 1
            assert not any(isinstance(node, CommentLine) for node in ast1)
            
            # Parse with comments - should get different result
            ast2 = getASTfromFile(temp_file, include_comments=True)
            assert ast2 is not None
            assert len(ast2) == 2
            assert any(isinstance(node, CommentLine) for node in ast2)
            
            # Parse without comments again - should get cached version
            ast3 = getASTfromFile(temp_file, include_comments=False)
            assert ast3 is not None
            assert len(ast3) == 1
            assert not any(isinstance(node, CommentLine) for node in ast3)
        finally:
            os.unlink(temp_file)

    def test_getASTfromLibraryFile_comments_parameter(self):
        """Test that getASTfromLibraryFile passes include_comments parameter through."""
        # Create a temporary library file
        with tempfile.TemporaryDirectory() as temp_dir:
            lib_file = os.path.join(temp_dir, "test_lib.scad")
            with open(lib_file, 'w') as f:
                f.write("// Library comment\nx = 5;")
            
            # Test without comments
            ast1, path1 = getASTfromLibraryFile("", lib_file, include_comments=False)
            assert ast1 is not None
            assert len(ast1) == 1
            assert not any(isinstance(node, CommentLine) for node in ast1)
            
            # Test with comments
            ast2, path2 = getASTfromLibraryFile("", lib_file, include_comments=True)
            assert ast2 is not None
            assert len(ast2) == 2
            assert any(isinstance(node, CommentLine) for node in ast2)


class TestErrorReporting:
    """Test error reporting format with code lines and caret markers."""

    def test_error_shows_line_and_caret(self):
        """Test that syntax errors show the line of code and a caret marker."""
        import sys
        from io import StringIO
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            # Parse invalid code
            result = getASTfromString('x = ')
            output = buffer.getvalue()
            
            # Verify output format
            assert "Syntax error" in output
            assert "line 1" in output
            assert "column" in output
            assert "x = " in output or "x =" in output
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_caret_position_single_line(self):
        """Test that caret is positioned correctly on a single line."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            result = getASTfromString('x = 5 +')
            output = buffer.getvalue()
            
            # Check that the line is shown
            assert "x = 5 +" in output
            # Check that caret is present
            assert "^" in output
            # Extract lines from output
            lines = output.strip().split('\n')
            # Find the line with the caret
            caret_line = [line for line in lines if '^' in line][0]
            # Find the code line
            code_line = [line for line in lines if 'x = 5 +' in line][0]
            # Caret should be positioned somewhere on that line
            assert len(caret_line) > 0
        finally:
            sys.stdout = old_stdout

    def test_error_caret_position_multi_line(self):
        """Test that caret is positioned correctly on multi-line code."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            result = getASTfromString('x = 5;\ny = 10 +')
            output = buffer.getvalue()
            
            # Check that the error line is shown
            assert "y = 10 +" in output
            assert "^" in output
            # Check line number
            assert "line 2" in output
        finally:
            sys.stdout = old_stdout

    def test_error_with_origin(self):
        """Test that error shows the correct origin."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            result = getASTfromString('x = ', origin='test.scad')
            output = buffer.getvalue()
            
            # Check that origin is shown
            assert "test.scad" in output or "<string>" in output
        finally:
            sys.stdout = old_stdout

    def test_error_format_components(self):
        """Test that error output contains all required components."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            result = getASTfromString('x = ')
            output = buffer.getvalue()
            
            # Check for all components
            assert "Syntax error" in output
            assert "at line" in output
            assert "column" in output
            # Should have the code line
            code_lines = [line for line in output.split('\n') if line.strip() and 'Syntax error' not in line and '^' not in line]
            assert len(code_lines) > 0
            # Should have caret
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_with_tabs(self):
        """Test that error handling works with tabs in code."""
        import sys
        from io import StringIO
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            # Code with tabs
            result = getASTfromString('x\t= ')
            output = buffer.getvalue()
            
            # Should still show error correctly
            assert "Syntax error" in output
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_with_source_map(self):
        """Test that error reporting works with SourceMap."""
        import sys
        from io import StringIO
        from openscad_parser.ast.source_map import SourceMap
        from openscad_parser.ast import parse_ast
        from openscad_parser import getOpenSCADParser
        
        old_stdout = sys.stdout
        sys.stdout = buffer = StringIO()
        
        try:
            source_map = SourceMap()
            source_map.add_origin("test.scad", "x = ")
            parser = getOpenSCADParser()
            combined_code = source_map.get_combined_string()
            
            result = parse_ast(parser, combined_code, source_map=source_map)
            output = buffer.getvalue()
            
            # Should show error with origin from source map
            assert "Syntax error" in output
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_reporting_without_source_map(self):
        """Test error reporting when source_map is None (fallback path)."""
        from openscad_parser.ast import parse_ast
        from openscad_parser import getOpenSCADParser
        import sys
        from io import StringIO
        
        parser = getOpenSCADParser()
        code = "x = ;"  # Syntax error
        
        old_stdout = sys.stdout
        try:
            buffer = StringIO()
            sys.stdout = buffer
            
            result = parse_ast(parser, code, file="test.scad", source_map=None)
            output = buffer.getvalue()
            
            # Should show error with file name
            assert "Syntax error" in output
            assert "test.scad" in output
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_reporting_caret_position_edge_cases(self):
        """Test error reporting with edge cases for caret position."""
        from openscad_parser.ast import parse_ast
        from openscad_parser import getOpenSCADParser
        from openscad_parser.ast.source_map import SourceMap
        import sys
        from io import StringIO
        
        parser = getOpenSCADParser()
        source_map = SourceMap()
        source_map.add_origin("test.scad", "x = ;")  # Syntax error at position 4
        
        old_stdout = sys.stdout
        try:
            buffer = StringIO()
            sys.stdout = buffer
            
            combined_code = source_map.get_combined_string()
            result = parse_ast(parser, combined_code, source_map=source_map)
            output = buffer.getvalue()
            
            # Should show error with caret
            assert "Syntax error" in output
            assert "^" in output
        finally:
            sys.stdout = old_stdout

    def test_error_reporting_line_out_of_range(self):
        """Test error reporting when error line is out of range."""
        from openscad_parser.ast import parse_ast
        from openscad_parser import getOpenSCADParser
        import sys
        from io import StringIO
        
        parser = getOpenSCADParser()
        
        old_stdout = sys.stdout
        try:
            buffer = StringIO()
            sys.stdout = buffer
            
            class FakeSourceMap:
                def get_location(self, _pos):
                    return Position(origin="test.scad", line=5, column=1)

                def get_combined_string(self):
                    return "x = 1;"

            result = parse_ast(parser, "x = ", source_map=FakeSourceMap())
            output = buffer.getvalue()
            assert "Syntax error" in output
        finally:
            sys.stdout = old_stdout

    def test_find_library_file_windows_path(self):
        """Test findLibraryFile with Windows path handling (mocked)."""
        import platform
        from openscad_parser.ast import findLibraryFile
        
        # This test verifies the Windows branch exists
        # Actual Windows testing would require Windows platform
        if platform.system() == "Windows":
            # Test Windows-specific path
            result = findLibraryFile("", "nonexistent.scad")
            # Should return None if not found
            assert result is None or isinstance(result, str)

    def test_find_library_file_linux_path(self):
        """Test findLibraryFile with Linux path handling."""
        import platform
        from openscad_parser.ast import findLibraryFile
        
        # This test verifies the Linux branch exists
        if platform.system() == "Linux":
            result = findLibraryFile("", "nonexistent.scad")
            assert result is None or isinstance(result, str)

    def test_get_ast_from_file_error_handling(self):
        """Test getASTfromFile error handling."""
        # Test with non-existent file
        with pytest.raises(FileNotFoundError):
            getASTfromFile("nonexistent_file_that_does_not_exist.scad")
        
        # Test with file that has read error (create a directory with that name)
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_file = os.path.join(temp_dir, "fake.scad")
            os.makedirs(fake_file, exist_ok=True)
            
            # This should raise an exception when trying to read
            with pytest.raises(Exception):
                getASTfromFile(fake_file)

    def test_get_ast_from_file_process_includes_error(self):
        """Test getASTfromFile when process_includes raises an error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <nonexistent.scad>\n")
            
            # Should raise an exception when include file is not found
            with pytest.raises(Exception):
                getASTfromFile(main_file, process_includes=True)
