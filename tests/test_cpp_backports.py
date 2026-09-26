"""Fixes backported from openscad_cpp_parser (and already in
openscad_lalr_parser); `#N` are cpp PRs."""
import os
import platform

import pytest

import openscad_parser.ast as ast_mod
from openscad_parser.ast import findLibraryFile, getASTfromLibraryFile, librarySearchDirs

BUNDLED = ast_mod._BUNDLED_LIBRARY_DIR


class TestLibrarySearch:
    """#10: OpenSCAD's own search order."""

    @pytest.fixture
    def home(self, tmp_path, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.delenv("OPENSCADPATH", raising=False)
        (tmp_path / "Documents" / "OpenSCAD" / "libraries").mkdir(parents=True)
        return tmp_path

    def test_openscadpath_comes_first_and_keeps_the_default(self, home, monkeypatch):
        env_dir = home / "extra"
        env_dir.mkdir()
        monkeypatch.setenv("OPENSCADPATH", str(env_dir))
        default = home / "Documents" / "OpenSCAD" / "libraries"
        (default / "BOSL2.scad").write_text("x = 1;")
        (default / "both.scad").write_text("x = 1;")
        (env_dir / "both.scad").write_text("x = 2;")
        main = home / "main.scad"
        assert librarySearchDirs(str(main)) == [str(home), str(env_dir), str(default), BUNDLED]
        assert findLibraryFile(str(main), "BOSL2.scad") == str(default / "BOSL2.scad")  # was hidden
        assert findLibraryFile(str(main), "both.scad") == str(env_dir / "both.scad")

    def test_windows_asks_for_documents(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setattr(ast_mod, "_windows_documents_dir", lambda: "D:\\OneDrive\\Documents")
        monkeypatch.delenv("OPENSCADPATH", raising=False)
        assert librarySearchDirs("") == [os.path.join("D:\\OneDrive\\Documents", "OpenSCAD", "libraries"), BUNDLED]

    def test_libraries_beside_the_package_are_searched_last(self, home, monkeypatch):
        bundled = home / "pkg" / "libraries"
        bundled.mkdir(parents=True)
        (bundled / "shipped.scad").write_text("x = 1;")
        (bundled / "both.scad").write_text("x = 2;")
        default = home / "Documents" / "OpenSCAD" / "libraries"
        (default / "both.scad").write_text("x = 1;")
        monkeypatch.setattr(ast_mod, "_BUNDLED_LIBRARY_DIR", str(bundled))
        main = str(home / "main.scad")
        assert findLibraryFile(main, "shipped.scad") == str(bundled / "shipped.scad")
        assert findLibraryFile(main, "both.scad") == str(default / "both.scad")

    def test_not_found_lists_every_directory(self, home):
        main = home / "main.scad"
        main.write_text("")
        with pytest.raises(FileNotFoundError) as e:
            getASTfromLibraryFile(str(main), "nope.scad")
        assert str(e.value) == ("Library file 'nope.scad' not found. Searched:\n"
                                f"  {home}\n  {home / 'Documents' / 'OpenSCAD' / 'libraries'}\n  {BUNDLED}")
