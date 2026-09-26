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


class TestRangeStepWritten:
    """ade1d62: a range records whether its step was written."""

    def _range(self, src):
        from openscad_parser.ast import getASTfromString
        return getASTfromString(f"x = {src};")[0].expr

    def test_flag_and_printing(self):
        two, three = self._range("[5:0]"), self._range("[5:1:0]")
        assert two.implicit_step and not three.implicit_step
        assert str(two) == "[5 : 0]" and str(three) == "[5 : 1 : 0]"
        assert two.step.val == 1  # the value is the same either way

    def test_survives_serialization(self):
        from openscad_parser.ast import ast_from_json, ast_to_json, getASTfromString
        ast = ast_from_json(ast_to_json(getASTfromString("x = [5:0]; y = [5:1:0];")))
        assert ast[0].expr.implicit_step and not ast[1].expr.implicit_step

    def test_pretty_print_keeps_the_written_form(self):
        from openscad_parser.ast import getASTfromString
        from openscad_parser.ast.pretty_print import to_openscad
        assert to_openscad(getASTfromString("for (i = [5:0]) cube(i);")).startswith("for (i = [5 : 0])")
        assert to_openscad(getASTfromString("for (i = [5:1:0]) cube(i);")).startswith("for (i = [5 : 1 : 0])")


class TestLineCommentRoundTrip:
    """89114d9: a `//` comment ends its line, so printing one inline swallowed
    whatever followed it. Printed code must reparse, keep every comment, and
    print identically a second time."""

    @pytest.mark.parametrize("src", [
        "foo(a // one\n, b // two\n, c);",
        "f(a, // one\n b);",
        "echo(a, // x\n b);",
        "assert(a, // c\n \"msg\");",
        "cube([1, // w\n 2, 3]);",
        "module m(a, // pa\n b) cube(1);",
        "function f(a, // pa\n b) = a;",
        "module m // after name\n(a) cube(1);",
        "function f // n\n(a) = a;",
        "module m(a) // post\n{ cube(1); }",
        "x = [1, // one\n 2];",
        "x = f(a, // one\n g(b, // two\n c));",
    ])
    def test_round_trip(self, src):
        import re
        from openscad_parser.ast import getASTfromString
        from openscad_parser.ast.pretty_print import to_openscad
        out = to_openscad(getASTfromString(src, include_comments=True))
        again = getASTfromString(out, include_comments=True)
        assert again is not None, out
        assert [c.strip() for c in re.findall(r"//[^\n]*", out)] == [c.strip() for c in re.findall(r"//[^\n]*", src)]
        assert to_openscad(again) == out


class TestPrecedenceInPrinting:
    """What the printer writes must mean what was parsed."""

    @pytest.mark.parametrize("src,want", [
        ("x = (a + b)[0];", "x = (a + b)[0]"),
        ("x = (a + b).y;", "x = (a + b).y"),
        ("x = (a ? b : c) ? d : e;", "x = (a ? b : c) ? d : e"),
        ("x = (function(y) y)(3);", "x = (function(y) y)(3)"),
        ("x = (let(a = 1) a) + 2;", "x = (let(a = 1) a) + 2"),
    ])
    def test_parens_kept(self, src, want):
        from openscad_parser.ast import getASTfromString
        assert str(getASTfromString(src)[0]) == want


class TestRenderExpression:
    """#5: `render() { ... }` in expression position."""

    def _expr(self, src):
        from openscad_parser.ast import getASTfromString
        ast = getASTfromString(src)
        assert ast is not None, src
        return ast[0].expr

    def test_parses_with_arguments_and_children(self):
        from openscad_parser.ast import RenderExpression, ModularCall, NamedArgument
        e = self._expr("obj = render(convexity=2) { cube(1); sphere(2); };")
        assert type(e) is RenderExpression
        assert [type(a) for a in e.arguments] == [NamedArgument]
        assert [c.name.name for c in e.children if isinstance(c, ModularCall)] == ["cube", "sphere"]

    def test_member_access_on_the_result(self):
        from openscad_parser.ast import PrimaryMember, RenderExpression
        e = self._expr("v = render() { cube(1); }.volume;")
        assert type(e) is PrimaryMember and type(e.left) is RenderExpression

    def test_render_is_still_a_name_and_a_call(self):
        # Unlike the LALR parsers, ordered choice needs no reserved word:
        # OpenSCAD itself accepts both of these.
        from openscad_parser.ast import ModularCall, NumberLiteral, PrimaryCall
        assert type(self._expr("render = 3;")) is NumberLiteral
        assert type(self._expr("x = render(4);")) is PrimaryCall
        from openscad_parser.ast import getASTfromString
        assert type(getASTfromString("render() cube(1);")[0]) is ModularCall

    @pytest.mark.parametrize("src", [
        "obj = render() { cube(1); };",
        "v = render() { translate([1, 0, 0]) cube(1); }.volume;",
        "o = render() { union() { cube(1); sphere(2); } };",
        "o = render() {};",
    ])
    def test_round_trips(self, src):
        from openscad_parser.ast import getASTfromString, ast_from_json, ast_to_json
        from openscad_parser.ast.pretty_print import to_openscad
        ast = getASTfromString(src)
        for text in (to_openscad(ast), str(ast[0]) + ";"):
            again = getASTfromString(text)
            assert again is not None, text
            assert to_openscad(again) == to_openscad(ast)
        assert to_openscad(ast_from_json(ast_to_json(ast))) == to_openscad(ast)

    def test_scopes_its_children(self):
        from openscad_parser.ast import getASTfromString, build_scopes
        ast = getASTfromString("r = 2; o = render() { sphere(r); };")
        build_scopes(ast)
        sphere = ast[1].expr.children[0]
        assert sphere.scope.lookup_variable("r") is ast[0]
