"""strict_commas(): the trailing commas OpenSCAD 2021.01 rejected, and only
those (openscad_cpp_parser #9's table, measured against 2021.01)."""
import pytest

from openscad_parser import strict_commas
from openscad_parser.ast import getASTfromFile, getASTfromString

REJECTED = ["cube(1,);", "translate([0,0,0],) cube(1);", "x = max(1, 2,);", 'x = str("a","b",);',
            "x = let(x=1, y=2,) x;", "for (i=[0:2],) cube(i);", "intersection_for(i=[0:1],) cube(i);"]
ACCEPTED = ["a = [2, 4,];", "a = [for (i=[0:2]) i,];", "a = [each [1,2],];", "module m(a, b,) {}",
            "function f(a, b,) = a;"]


@pytest.mark.parametrize("src", REJECTED)
def test_rejected_only_when_strict(src, capsys):
    assert getASTfromString(src) is not None
    with strict_commas():
        assert getASTfromString(src) is None


@pytest.mark.parametrize("src", ACCEPTED)
def test_accepted_either_way(src):
    with strict_commas():
        assert getASTfromString(src) is not None


def test_scope_restores_even_when_the_body_raises():
    with pytest.raises(RuntimeError):
        with strict_commas():
            raise RuntimeError
    assert getASTfromString("cube(1,);") is not None


def test_a_file_parsed_leniently_is_not_served_to_a_strict_parse(tmp_path, capsys):
    f = tmp_path / "t.scad"
    f.write_text("cube(1,);\n")
    assert getASTfromFile(str(f)) is not None
    with strict_commas():
        assert getASTfromFile(str(f)) is None
    assert getASTfromFile(str(f)) is not None


def test_also_exported_from_the_ast_package():
    from openscad_parser.ast import strict_commas as from_ast
    assert from_ast is strict_commas


def test_disk_cache_keys_on_mode_and_parser_version(tmp_path, monkeypatch):
    import openscad_parser.ast as ast_mod
    monkeypatch.setenv("OPENSCAD_PARSER_CACHE_DIR", str(tmp_path))
    f = str(tmp_path / "t.scad")
    lenient = ast_mod._disk_cache_path(f, False)
    with strict_commas():
        assert ast_mod._disk_cache_path(f, False) != lenient
    monkeypatch.setattr(ast_mod, "_ast_format_tag", lambda: "another-version")
    assert ast_mod._disk_cache_path(f, False) != lenient
