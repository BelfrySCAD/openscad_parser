"""Tests for source map functionality, including include processing."""

import os
import tempfile
import pytest
from openscad_parser.ast.source_map import SourceMap, process_includes, SourceLocation


class TestSourceMapBasic:
    """Test basic SourceMap functionality."""

    def test_add_origin(self):
        """Test adding origins to source map."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        
        assert len(source_map.get_segments()) == 1
        assert source_map.get_combined_string() == "x = 5;\n"

    def test_get_location(self):
        """Test getting location from position."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        
        loc = source_map.get_location(0)
        assert loc.origin == "main.scad"
        assert loc.line == 1
        assert loc.column == 1
        
        loc = source_map.get_location(4)
        assert loc.origin == "main.scad"
        assert loc.line == 1
        assert loc.column == 5

    def test_multiple_origins(self):
        """Test multiple origins."""
        source_map = SourceMap()
        source_map.add_origin("main.scad", "x = 5;\n")
        source_map.add_origin("lib.scad", "y = 10;\n", insert_at=8)
        
        combined = source_map.get_combined_string()
        assert "x = 5;\n" in combined
        assert "y = 10;\n" in combined
        
        # Check locations
        loc = source_map.get_location(8)
        assert loc.origin == "lib.scad"


class TestProcessIncludes:
    """Test process_includes function."""

    def test_simple_include(self):
        """Test processing a simple include statement."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "z = 20;\n" in result
            assert "y = 10;\n" in result
            assert "include <lib.scad>" not in result

    def test_nested_includes(self):
        """Test nested include statements."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib1_file = os.path.join(temp_dir, "lib1.scad")
            lib2_file = os.path.join(temp_dir, "lib2.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib1.scad>\n")
            
            with open(lib1_file, 'w') as f:
                f.write("y = 10;\ninclude <lib2.scad>\nz = 15;\n")
            
            with open(lib2_file, 'w') as f:
                f.write("w = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "y = 10;\n" in result
            assert "w = 20;\n" in result
            assert "z = 15;\n" in result
            assert "include" not in result

    def test_multiple_includes(self):
        """Test multiple include statements in one file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib1_file = os.path.join(temp_dir, "lib1.scad")
            lib2_file = os.path.join(temp_dir, "lib2.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib1.scad>\ny = 10;\ninclude <lib2.scad>\nz = 15;\n")
            
            with open(lib1_file, 'w') as f:
                f.write("a = 1;\n")
            
            with open(lib2_file, 'w') as f:
                f.write("b = 2;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "a = 1;\n" in result
            assert "y = 10;\n" in result
            assert "b = 2;\n" in result
            assert "z = 15;\n" in result
            assert "include" not in result

    def test_include_in_string_ignored(self):
        """Test that includes in strings are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write('x = 5;\n"include <lib.scad>"\ninclude <lib.scad>\n')
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # The include in the string should remain, the real one should be replaced
            assert '"include <lib.scad>"' in result
            assert "z = 20;\n" in result
            # Should only have one include left (the one in the string)
            assert result.count("include <lib.scad>") == 1

    def test_include_in_single_line_comment_ignored(self):
        """Test that includes in single-line comments are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\n// include <lib.scad>\ninclude <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "// include <lib.scad>" in result
            assert "z = 20;\n" in result
            assert result.count("include <lib.scad>") == 1  # Only the one in comment

    def test_include_in_multi_line_comment_ignored(self):
        """Test that includes in multi-line comments are ignored."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\n/* include <lib.scad> */\ninclude <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "/* include <lib.scad> */" in result
            assert "z = 20;\n" in result
            assert result.count("include <lib.scad>") == 1  # Only the one in comment

    def test_include_file_not_found(self):
        """Test that FileNotFoundError is raised when include file is not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <nonexistent.scad>\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            with pytest.raises(FileNotFoundError) as exc_info:
                process_includes(source_map, main_file)
            
            assert "nonexistent.scad" in str(exc_info.value)

    def test_circular_includes_prevention(self):
        """Test that circular includes are prevented by max_iterations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("include <lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("include <main.scad>\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            with pytest.raises(ValueError) as exc_info:
                process_includes(source_map, main_file, max_iterations=10)
            
            assert "Maximum iterations" in str(exc_info.value)

    def test_include_with_path(self):
        """Test include with a path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_dir = os.path.join(temp_dir, "lib")
            os.makedirs(lib_dir)
            lib_file = os.path.join(lib_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib/lib.scad>\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "z = 20;\n" in result
            assert "include <lib/lib.scad>" not in result

    def test_include_preserves_source_locations(self):
        """Test that source locations are preserved after processing includes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            
            # Check that we can still get locations
            loc = source_map.get_location(0)
            assert loc.origin == main_file
            assert loc.line == 1
            assert loc.column == 1
            
            # Location in included file
            result = source_map.get_combined_string()
            lib_pos = result.find("z = 20")
            if lib_pos >= 0:
                loc = source_map.get_location(lib_pos)
                assert loc.origin == lib_file

    def test_include_with_whitespace(self):
        """Test include statement with various whitespace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude   <lib.scad>\n")  # Extra spaces
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "z = 20;\n" in result
            assert "include" not in result or "include   <lib.scad>" not in result

    def test_include_with_tabs(self):
        """Test include statement with tabs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude\t<lib.scad>\n")  # Tab instead of space
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "z = 20;\n" in result

    def test_escaped_quotes_in_string(self):
        """Test that escaped quotes in strings don't break string detection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write('x = "include <lib.scad>";\ninclude <lib.scad>\n')  # Escaped quote scenario
            
            with open(lib_file, 'w') as f:
                f.write("z = 20;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # The include in the string should remain
            assert '"include <lib.scad>"' in result or 'x = "include <lib.scad>";' in result
            # The real include should be processed
            assert "z = 20;\n" in result

    def test_no_includes(self):
        """Test processing a file with no includes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ny = 10;\n")
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            original = source_map.get_combined_string()
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            # Should be unchanged
            assert result == original

    def test_empty_included_file(self):
        """Test including an empty file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            main_file = os.path.join(temp_dir, "main.scad")
            lib_file = os.path.join(temp_dir, "lib.scad")
            
            with open(main_file, 'w') as f:
                f.write("x = 5;\ninclude <lib.scad>\ny = 10;\n")
            
            with open(lib_file, 'w') as f:
                f.write("")  # Empty file
            
            source_map = SourceMap()
            with open(main_file, 'r') as f:
                source_map.add_origin(main_file, f.read())
            
            source_map = process_includes(source_map, main_file)
            result = source_map.get_combined_string()
            
            assert "x = 5;\n" in result
            assert "y = 10;\n" in result
            assert "include <lib.scad>" not in result
