import argparse
from typing import Dict, List, Optional, Any, Union

from openscad_parser import getOpenSCADParser
from arpeggio import PTNodeVisitor, visit_parse_tree, NoMatch
from pathlib import Path
import os
import os.path
import platform


class ItemDecl():
    def __init__(self, name: str, file: Optional[str]) -> None:
        self.name = name
        self.file = file


class OpenSCADDependencyVisitor(PTNodeVisitor):
    def __init__(self, startfile: str, parser: Any = None, defaults: bool = True, debug: bool = False) -> None:
        super().__init__(defaults=defaults, debug=debug)
        self.load_stack: List[str] = [os.path.abspath(startfile)]
        self.current_file = None
        self.declared_functions: Dict[str, ItemDecl] = {}
        self.declared_modules: Dict[str, ItemDecl] = {}
        self.func_calls: Dict[str, Dict[str, ItemDecl]] = {}
        self.mod_calls: Dict[str, Dict[str, ItemDecl]] = {}
        self.parser: Any = parser
        self.builtin_funcs: Dict[str, int] = {}
        self.builtin_modules: Dict[str, int] = {}
        self.file_nodes: Dict[str, str] = {}
        self.node_files: Dict[str, str] = {}
        self.node_num: int = 1
        self.filenodes: List[str] = []
        self.ext_calls_in_file: Dict[str, Dict[str, List[str]]] = {}   # [file][type]: [called_names]
        self.called_files: Dict[str, Dict[str, List[str]]] = {}
        for name in [
            "concat", "lookup", "str", "chr", "ord", "search", "version",
            "version_num", "parent_module", "abs", "sign", "sin", "cos",
            "tan", "acos", "asin", "atan", "atan2", "floor", "round",
            "ceil", "ln", "len", "let", "log", "pow", "sqrt", "exp",
            "rands", "min", "max", "norm", "cross", "is_undef",
            "is_bool", "is_num", "is_string", "is_list", "is_function",
            "text_metrics",
        ]:
            self.builtin_funcs[name] = 1
        for name in [
            "render", "children", "circle", "square", "polygon", "text",
            "import", "projection", "sphere", "cube", "cylinder",
            "polyhedron", "linear_extrude", "rotate_extrude", "surface",
            "roof", "translate", "rotate", "scale", "resize", "mirror",
            "multmatrix", "color", "offset", "hull", "minkowski", "union",
            "difference", "intersection",
        ]:
            self.builtin_modules[name] = 1

    def get_relfile(self, filename: str) -> Path:
        try:
            cwpath = Path(os.getcwd())
            abspath = Path(filename)
            relpath = abspath.relative_to(cwpath)
        except ValueError:
            relpath = Path(filename)
        return relpath

    def register_file(self, filename: str) -> None:
        if filename not in self.file_nodes:
            node_name = f"file{self.node_num}"
            self.file_nodes[filename] = node_name
            self.node_files[node_name] = filename
            self.filenodes.append(node_name)
            self.node_num += 1

    def dot_node(self, name: str, indent: int = 4, **kwargs) -> str:
        out = " " * indent + name
        if kwargs:
            attr_str = ", ".join('{}="{}"'.format(key, val.replace('\\', '\\\\').replace('"', '\\"')) for key, val in kwargs.items())
            out += f" [{attr_str}]"
        out += "\n"
        return out

    def dot_edge(self, nodes: List[str], indent: int = 4, **kwargs) -> str:
        out = " " * indent
        out += " -> ".join(nodes)
        out += self.dot_node("", indent=0, **kwargs)
        return out

    def analyze_external_calls(self) -> None:
        files = sorted(
            list(set(
                list(self.func_calls.keys()) +
                list(self.mod_calls.keys())
            ))
        )
        self.ext_calls_in_file = {}   # [calling_file][type]: [called_names]
        for calling_file in files:
            ext_funcs = []
            if calling_file in self.func_calls:
                for called_func in self.func_calls[calling_file].keys():
                    item = self.declared_functions.get(called_func)
                    if item is None or item.file != calling_file:
                        ext_funcs.append(called_func)
            ext_funcs = sorted(list(set(ext_funcs)))

            ext_mods = []
            if calling_file in self.mod_calls:
                for name in self.mod_calls[calling_file]:
                    item = self.declared_modules.get(name)
                    if item is None or item.file != calling_file:
                        ext_mods.append(name)
            ext_mods = sorted(list(set(ext_mods)))

            self.ext_calls_in_file[calling_file] = {
                "func_calls": ext_funcs,
                "mod_calls": ext_mods,
            }

        self.called_files = {}
        for calling_file in files:
            if calling_file not in self.ext_calls_in_file:
                continue

            if calling_file not in self.called_files:
                self.called_files[calling_file] = {}

            for called_function in self.ext_calls_in_file[calling_file]["func_calls"]:
                item = self.declared_functions.get(called_function)
                called_file = None if item is None else item.file
                if called_file is None:
                    called_file = "UNDECLARED"
                if called_file not in self.called_files[calling_file]:
                    self.called_files[calling_file][called_file] = []
                self.called_files[calling_file][called_file].append(called_function)

            for called_module in self.ext_calls_in_file[calling_file]["mod_calls"]:
                item = self.declared_modules.get(called_module)
                called_file = None if item is None else item.file
                if called_file is None:
                    called_file = "UNDECLARED"
                if called_file not in self.called_files[calling_file]:
                    self.called_files[calling_file][called_file] = []
                self.called_files[calling_file][called_file].append(called_module)

    def get_results(self, dot_file: Optional[str] = None) -> str:
        out = "\n"

        self.analyze_external_calls()

        for filenode in self.filenodes:
            calling_file = self.node_files[filenode]
            if calling_file not in self.ext_calls_in_file:
                continue

            relfile = self.get_relfile(calling_file)
            out += f"File '{relfile}' externally references:\n"

            for called_file in self.called_files[calling_file]:
                relfile = self.get_relfile(called_file)
                called_names = sorted(list(set(self.called_files[calling_file][called_file])))
                calls = ", ".join(f"{called_name}()" for called_name in called_names)
                out += f"    {relfile}: {calls}\n"

        if dot_file:
            try:
                with open(dot_file, "w") as f:
                    f.write('digraph Dependencies {\n')
                    f.write('    rankdir="BT"\n')
                    f.write('\n')
                    f.write('    // File nodes\n')
                    for filenode in self.filenodes:
                        calling_file = self.node_files[filenode]
                        relfile = str(self.get_relfile(calling_file)).replace('"', r'\"')
                        f.write(self.dot_node(filenode, label=relfile))

                    f.write('\n')
                    f.write('    // Relations\n')
                    callnode_num = 1
                    for filenode in self.filenodes:
                        calling_file = self.node_files[filenode]
                        for called_file in self.called_files[calling_file]:
                            called_names = sorted(list(set(self.called_files[calling_file][called_file])))
                            calls = " | ".join(f"{called_name}()" for called_name in called_names)
                            callnode = f"calls{callnode_num}"
                            callnode_num += 1
                            f.write(self.dot_node(callnode, shape="record", label=f"{{{calls}}}"))
                            to_node = self.file_nodes.get(called_file)
                            if to_node is None:
                                f.write(self.dot_edge([filenode, callnode], color="0x77f"))
                            else:
                                f.write(self.dot_edge([filenode, callnode, to_node]))

                    f.write("}\n")
            except IOError as e:
                print(f"An IOError occurred: {e}")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")

        return out

    def _find_libfile(self, currfile: str, libfile: str) -> Optional[str]:
        dirs = []
        if currfile:
            dirs.append(os.path.dirname(os.path.abspath(currfile)))
        pathsep = ":"
        dflt_path = ""
        if platform.system() == "Windows":
            dflt_path = r'My Documents\OpenSCAD\libraries'
            pathsep = ";"
        elif platform.system() == "Darwin":
            dflt_path = "$HOME/Documents/OpenSCAD/libraries"
        elif platform.system() == "Linux":
            dflt_path = "$HOME/.local/share/OpenSCAD/libraries"
        env = os.getenv("OPENSCADPATH", dflt_path)
        if env:
            for path in env.split(pathsep):
                dirs.append(os.path.expandvars(path))
        for d in dirs:
            test_file = os.path.join(d, libfile)
            if os.path.isfile(test_file):
                return test_file
        return None

    def _print_syntax_error(self, file: str, e: NoMatch) -> None:
        snippet = e.parser.input[e.position-e.col+1:].split("\n")[0] + \
            "\n" + " "*(e.col-1) + "^"
        print("Syntax Error at {}, line {}, col {}:\n{}".format(
            file, e.line, e.col, snippet))

    def visit_use_statement(self, node, children):
        oldfile = self.current_file
        if oldfile is None:
            return node
        self.current_file = self._find_libfile(oldfile, children[1])
        if self.current_file is None:
            return node
        if self.current_file not in self.func_calls:
            self.func_calls[self.current_file] = {}
        if self.current_file not in self.mod_calls:
            self.mod_calls[self.current_file] = {}
        try:
            print("Using {}".format(self.get_relfile(self.current_file)))
            if self.current_file in self.load_stack:
                print("Circular include/use detected:")
                self.load_stack.append(self.current_file)
                for stackfile in self.load_stack:
                    print(f"  {stackfile}")
                print()
                return node
            self.load_stack.append(self.current_file)
            with open(self.current_file, 'r') as f:
                self.register_file(self.current_file)
                if self.parser is None:
                    raise ValueError("Parser is not initialized")
                parse_tree = self.parser.parse(f.read())
                visit_parse_tree(parse_tree, self)
        except NoMatch as e:
            self._print_syntax_error(self.current_file, e)
        self.current_file = oldfile
        return node

    def visit_include_statement(self, node, children):
        oldfile = self.current_file
        if oldfile is None:
            return node
        self.current_file = self._find_libfile(oldfile, children[1])
        if self.current_file is None:
            return node
        if self.current_file not in self.func_calls:
            self.func_calls[self.current_file] = {}
        if self.current_file not in self.mod_calls:
            self.mod_calls[self.current_file] = {}
        try:
            print("Including {}".format(self.get_relfile(self.current_file)))
            if self.current_file in self.load_stack:
                print("Circular include/use detected:")
                self.load_stack.append(self.current_file)
                for stackfile in self.load_stack:
                    print(f"  {stackfile}")
                print()
                return node
            self.load_stack.append(self.current_file)
            with open(self.current_file, 'r') as f:
                self.register_file(self.current_file)
                if self.parser is None:
                    raise ValueError("Parser is not initialized")
                parse_tree = self.parser.parse(f.read())
                visit_parse_tree(parse_tree, self)
        except NoMatch as e:
            self._print_syntax_error(self.current_file, e)
        self.current_file = oldfile
        return node

    def visit_module_definition(self, node, children):
        declared_name = children[1]
        self.declared_modules[declared_name] = ItemDecl(declared_name, self.current_file)
        return node

    def visit_function_definition(self, node, children):
        declared_name = children[1]
        self.declared_functions[declared_name] = ItemDecl(declared_name, self.current_file)
        return node

    # Module call.
    def visit_modular_call(self, node, children):
        called_name = children[0]
        if self.current_file is None:
            return node
        if called_name not in self.builtin_modules:
            if self.current_file not in self.mod_calls:
                self.mod_calls[self.current_file] = {}
            self.mod_calls[self.current_file][called_name] = \
                ItemDecl(called_name, self.current_file)
        return node

    # expression call level precedence
    def visit_prec_call(self, node, children):
        if len(children) > 1 and children[1][0] == '(':
            # Function call in expression.
            called_name = children[0]
            if self.current_file is None:
                return node
            if called_name not in self.builtin_funcs:
                if self.current_file not in self.func_calls:
                    self.func_calls[self.current_file] = {}
                self.func_calls[self.current_file][called_name] = \
                    ItemDecl(called_name, self.current_file)
        return node


    def visit_call_expr(self, node, children):
        return node



def main() -> None:
    arg_parser = argparse.ArgumentParser(prog='openscad_depends')
    arg_parser.add_argument('-d', '--dot-file', default=None,
                        help='Write a GraphViz style DOT digraph chart to the given file.')
    arg_parser.add_argument('file', help='Input file.')

    opts = arg_parser.parse_args()

    oscad_parser = getOpenSCADParser(reduce_tree=False, debug=False)
    visitor = OpenSCADDependencyVisitor(startfile=opts.file, debug=False, parser=oscad_parser)
    try:
        with open(opts.file, 'r') as f:
            visitor.current_file = os.path.abspath(opts.file)
            visitor.register_file(visitor.current_file)
            parse_tree = oscad_parser.parse(f.read())
            visit_parse_tree(parse_tree, visitor)
    except NoMatch as e:
        visitor._print_syntax_error(opts.file, e)
    print(visitor.get_results(dot_file=opts.dot_file))


if __name__ == "__main__":
    main()

# vim: set ts=4 sw=4 expandtab:
