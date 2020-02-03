# Copyright (C) 2016-2020 H. Turgut Uyar <uyar@tekir.org>
#
# pygenstub is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pygenstub is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pygenstub.  If not, see <http://www.gnu.org/licenses/>.

"""A utility for generating stub files from signature comments."""

import ast
import builtins
import os
import re
import sys
from argparse import ArgumentParser
from bisect import bisect
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
from pathlib import Path
from pkgutil import get_loader, walk_packages


# sigalias: ParsedParameter = Tuple[str, str, bool]
# sigalias: FunctionDef = Union[ast.FunctionDef, ast.AsyncFunctionDef]


__version__ = "2.0.0a2"  # sig: str


_BUILTIN_TYPES = {k for k, t in builtins.__dict__.items() if isinstance(t, type)}
_BUILTIN_TYPES.add("None")

_SIG_COMMENT = "# sig:"

_SUPPORTED_DECORATORS = {"property", "staticmethod", "classmethod"}

INDENT = 4 * " "

_EDIT_WARNING = "THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY."

_RE_SIG_COMMENT = re.compile(r"\s*#\s*([^\s]*)\s*::\s*(.*)?")
_RE_SIGALIAS_COMMENT = re.compile(r"\s*#\s*sigalias\s*:\s*(\w+)\s*=\s*(.*)\s*")

_RE_QUALIFIED_TYPES = re.compile(r"\w+(?:\.\w+)*")
_RE_COMMENT_IN_STRING = re.compile(r"""['"]\s*%(text)s\s*.*['"]""" % {"text": _SIG_COMMENT})
_RE_SIG_ARROW = re.compile(r"\s+->\s+")


############################################################
# SIGNATURE PROCESSING
############################################################


# _split_types:: (str) -> List[str]
def _split_types(decl):
    """Split a parameter types declaration into individual types."""
    if decl == "":
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for pos, char in enumerate(decl):
        if (char == ",") and (bracket_depth == 0):
            commas.append(pos)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1

    types = []
    last_pos = 0
    for pos in commas:
        types.append(decl[last_pos:pos].strip())
        last_pos = pos + 1
    else:
        types.append(decl[last_pos:].strip())
    return types


# parse_signature:: (str) -> Tuple[Optional[List[str]], str, Set[str]]
def parse_signature(signature):
    """Parse input and return parameter types from a signature.

    When parsing a signature comment, the type of the variable
    will be returned as the return type, and the input parameter types
    will be None.

    This will also collect the types that are required by any of the input
    and return types.

    :param signature: Signature to parse.
    :return: Input parameter types, return type, and all required types.
    :raise ValueError: When signature cannot be correctly parsed.
    """
    sig_parts = _RE_SIG_ARROW.split(signature)
    if len(sig_parts) > 2:
        raise ValueError("multiple arrows in signature")
    if len(sig_parts) == 1:
        # signature comment: no parameters, variable type is return type
        param_types, return_type = None, signature.strip()
    else:
        lhs, return_type = [s.strip() for s in sig_parts]
        if (lhs[0] != "(") or (lhs[-1] != ")"):
            raise ValueError("missing parentheses around parameter list in signature")
        csv = lhs[1:-1].strip()  # remove the parentheses around the parameter type list
        param_types = _split_types(csv)
    requires = set(_RE_QUALIFIED_TYPES.findall(signature))
    return param_types, return_type, requires


############################################################
# STUB TREE MODEL
############################################################


class StubNode:
    """A node in a stub tree."""

    # StubNode.__init__:: (str) -> None
    def __init__(self, name):
        self.name = name  # sig: str
        self.parent = None  # sig: Optional[StubNode]
        self.children = []  # sig: List[StubNode]

    # StubNode.add_child:: (StubNode) -> None
    def add_child(self, node):
        node.parent = self
        self.children.append(node)

    # StubNode.print_stub:: (str) -> None
    def print_stub(self, indent=""):
        variables = [n for n in self.children if isinstance(n, VariableNode)]
        for child in variables:
            child.print_stub(indent=indent)

        nonvariables = [n for n in self.children if not isinstance(n, VariableNode)]
        for child in nonvariables:
            child.print_stub(indent=indent)


class VariableNode(StubNode):
    """A node representing an assignment in a stub tree."""

    # VariableNode.__init__:: (str, str) -> None
    def __init__(self, name, type_):
        super().__init__(name)
        self.type_ = type_  # sig: str

    # VariableNode.print_stub:: (str) -> None
    def print_stub(self, indent=""):
        line = "%(name)s: %(type)s" % {"name": self.name, "type": self.type_}
        print(indent, line, sep="")


class FunctionNode(StubNode):
    """A node representing a function in a stub tree."""

    # FunctionNode.__init__:: (str, List[ParsedParameter], str, Optional[List[str]]) -> None
    def __init__(self, name, parameters, rtype, *, decorators=None):
        """Initialize this function node.

        Parameters have to given as triples where each item specifies
        the name of the parameter, its type, and whether it has a default value or not.

        :param name: Name of function.
        :param parameters: Parameter triples (name, type, has_default).
        :param rtype: Type of return value.
        :param decorators: Decorators of function.
        """
        super().__init__(name)
        self.async_ = False  # sig: bool
        self.parameters = parameters  # sig: List[ParsedParameter]
        self.rtype = rtype  # sig: str
        self.decorators = decorators if decorators is not None else []  # sig: List[str]

    # FunctionNode.print_stub:: (str) -> None
    def print_stub(self, indent=""):
        for deco in self.decorators:
            if (deco in _SUPPORTED_DECORATORS) or deco.endswith(".setter"):
                print(indent, "@" + deco, sep="")

        parameters = []
        for name, type_, has_default in self.parameters:
            decl = "%(name)s%(type)s%(default)s" % {
                "name": name,
                "type": ": " + type_ if type_ else "",
                "default": " = ..." if has_default else "",
            }
            parameters.append(decl)

        line = "%(async)sdef %(name)s(%(params)s) -> %(return)s: ..." % {
            "async": "async " if self.async_ else "",
            "name": self.name,
            "params": ", ".join(parameters),
            "return": self.rtype,
        }
        print(indent, line, sep="")


class ClassNode(StubNode):
    """A node representing a class in a stub tree."""

    # ClassNode.__init__:: (str, List[str], Optional[str]) -> None
    def __init__(self, name, *, bases, signature=None):
        """Initialize this class node.

        :param name: Name of class.
        :param bases: Base classes of class.
        :param signature: Signature of class, to be used in __init__ method.
        """
        super().__init__(name)
        self.bases = bases  # sig: List[str]
        self.signature = signature  # sig: Optional[str]

    # ClassNode.print_stub:: (str) -> None
    def print_stub(self, indent=""):
        slots = {
            "name": self.name,
            "bases": ("(" + ", ".join(self.bases) + ")") if len(self.bases) > 0 else "",
        }
        if len(self.children) == 0:
            print(indent, "class %(name)s%(bases)s: ..." % slots, sep="")
        else:
            print(indent, "class %(name)s%(bases)s:" % slots, sep="")
            super().print_stub(indent=indent + INDENT)


############################################################
# AST PROCESSING
############################################################


# _get_args:: (FunctionDef) -> List[Tuple[Tuple[int, int], str]]
def _get_args(node):
    args = [((arg.lineno, arg.col_offset), arg.arg) for arg in node.args.args]
    if node.args.vararg is not None:
        arg = node.args.vararg
        args.append(((arg.lineno, arg.col_offset), "*" + arg.arg))
    kwonlyargs = node.args.kwonlyargs
    if (node.args.vararg is None) and (len(kwonlyargs) > 0):
        arg = kwonlyargs[0]
        args.append(((arg.lineno, arg.col_offset - 1), "*"))
    args.extend(((arg.lineno, arg.col_offset), arg.arg) for arg in kwonlyargs)
    if node.args.kwarg is not None:
        arg = node.args.kwarg
        args.append(((arg.lineno, arg.col_offset), "**" + arg.arg))
    return args


# get_decorators:: (FunctionDef) -> List[str]
def _get_decorators(node):
    decorators = []
    for d in node.decorator_list:
        if hasattr(d, "id"):
            decorators.append(d.id)
        elif hasattr(d, "func"):
            decorators.append(d.func.id)
        elif hasattr(d, "value"):
            decorators.append(d.value.id + "." + d.attr)
    return decorators


# _print_import_from:: (str, Set[str], str) -> None
def _print_import_from(mod, names, *, indent=""):
    regular = sorted(name for name in names if "::" not in name)
    if len(regular) > 0:
        line = "from %(mod)s import %(names)s" % {"mod": mod, "names": ", ".join(regular)}
        print(indent, line, sep="")

    renamed = [name for name in names if "::" in name]
    for as_name in renamed:
        new, old = as_name.split("::")
        line = "from %(mod)s import %(old)s as %(new)s" % {"mod": mod, "old": old, "new": new}
        print(indent, line, sep="")


class StubGenerator(ast.NodeVisitor):
    """A transformer that generates stub declarations from a source code."""

    # StubGenerator.__init__:: (str, bool) -> None
    def __init__(self, source, *, generic=False):
        """Initialize this stub generator.

        :param source: Source code to generate the stub for.
        :param generic: Whether to produce generic stubs.
        """
        self.root = StubNode("")  # sig: StubNode

        self.generic = generic  # sig: bool

        self.imported_namespaces = {}  # sig: Dict[str, str]
        self.imported_names = {}  # sig: Dict[str, str]
        self.defined_types = set()  # sig: Set[str]
        self.required_types = set()  # sig: Set[str]

        self._parents = [self.root]  # sig: List[StubNode]
        self._code_lines = source.splitlines()  # sig: List[str]

        self.aliases = {}  # sig: Dict[str, str]
        self.collect_aliases()

        self.signatures = {}  # sig: Dict[str, str]
        self.collect_signatures()

        ast_tree = ast.parse(source)
        self.visit(ast_tree)

    # StubGenerator.collect_aliases:: () -> None
    def collect_aliases(self):
        for line in self._code_lines:
            match = _RE_SIGALIAS_COMMENT.match(line)
            if match:
                alias, signature = match.groups()
                self.aliases[alias] = signature
        for alias, signature in self.aliases.items():
            _, _, requires = parse_signature(signature)
            self.required_types |= requires
            self.defined_types |= {alias}

    # StubGenerator.collect_signatures:: () -> None
    def collect_signatures(self):
        n_lines = len(self._code_lines)
        i = 0
        while i < n_lines:
            line = self._code_lines[i]
            match = _RE_SIG_COMMENT.match(line)
            if match:
                j = i + 1
                while j < n_lines:
                    next_line = self._code_lines[j].strip()
                    if not next_line.startswith("#"):
                        break
                    line += next_line[1:]
                    j += 1
                if j > i + 1:
                    # multiline signature, match again
                    match = _RE_SIG_COMMENT.match(line)
                    i = j - 1
                name, signature = match.groups()
                self.signatures[name] = signature
            i += 1

    def visit_Import(self, node):
        line = self._code_lines[node.lineno - 1]
        module_name = line.split("import")[0].strip()
        for name in node.names:
            imported_name = name.name
            if name.asname:
                imported_name = name.asname + "::" + imported_name
            self.imported_namespaces[imported_name] = module_name

    def visit_ImportFrom(self, node):
        line = self._code_lines[node.lineno - 1]
        module_name = line.split("from")[1].split("import")[0].strip()
        for name in node.names:
            imported_name = name.name
            if name.asname:
                imported_name = name.asname + "::" + imported_name
            self.imported_names[imported_name] = module_name

    def visit_Assign(self, node):
        line = self._code_lines[node.lineno - 1]
        if _SIG_COMMENT in line:
            line = _RE_COMMENT_IN_STRING.sub("", line)

        if (_SIG_COMMENT not in line) and (not self.generic):
            return

        if _SIG_COMMENT in line:
            _, signature = line.split(_SIG_COMMENT)
            _, return_type, requires = parse_signature(signature)
            self.required_types |= requires

        parent = self._parents[-1]
        for var in node.targets:
            if isinstance(var, ast.Name):
                name, p = var.id, parent
            elif (
                isinstance(var, ast.Attribute)
                and isinstance(var.value, ast.Name)
                and (var.value.id == "self")
            ):
                name, p = var.attr, parent.parent
            else:
                name, p = None, None

            if name is not None:
                if self.generic:
                    return_type = "Any"
                    self.required_types.add(return_type)
                stub_node = VariableNode(name, return_type)
                p.add_child(stub_node)

    # StubGenerator.get_function_node:: (FunctionDef) -> Optional[FunctionNode]
    def get_function_node(self, node):
        signature_key = node.name
        if isinstance(self._parents[-1], ClassNode):
            signature_key = self._parents[-1].name + "." + node.name
        signature = self.signatures.get(signature_key)

        if signature is None:
            parent = self._parents[-1]
            if isinstance(parent, ClassNode) and (node.name == "__init__"):
                signature = parent.signature

        if (signature is None) and (not self.generic):
            return None

        args = _get_args(node)
        arg_locs, arg_names = zip(*args)
        n_args = len(args)

        if signature is None:
            arg_types, rtype, requires = ["Any"] * n_args, "Any", {"Any"}
        else:
            input_types, rtype, requires = parse_signature(signature)
            arg_types = input_types if input_types is not None else []

        decorators = _get_decorators(node)

        # TODO: only in classes
        if ((n_args > 0) and (arg_names[0] == "self")) or (
            (n_args > 0) and (arg_names[0] == "cls") and ("classmethod" in decorators)
        ):
            if signature is None:
                arg_types[0] = ""
            else:
                arg_types.insert(0, "")

        try:
            kwonly_pos = arg_names.index("*")
            arg_types.insert(kwonly_pos, "")
        except ValueError:
            pass

        self.required_types |= requires

        if len(arg_types) != len(arg_names):
            raise ValueError("Parameter names and types don't match: " + node.name)

        arg_defaults = {
            bisect(arg_locs, (d.lineno, d.col_offset)) - 1 for d in node.args.defaults
        }

        kw_defaults = node.args.kw_defaults
        for i, d in enumerate(kw_defaults):
            if d is not None:
                arg_defaults.add(len(node.args.args) + i + 1)

        params = [
            (name, type_, i in arg_defaults)
            for i, (name, type_) in enumerate(zip(arg_names, arg_types))
        ]

        stub_node = FunctionNode(
            node.name, parameters=params, rtype=rtype, decorators=decorators
        )
        self._parents[-1].add_child(stub_node)

        self._parents.append(stub_node)
        self.generic_visit(node)
        del self._parents[-1]
        return stub_node

    def visit_FunctionDef(self, node):
        node = self.get_function_node(node)
        if node is not None:
            node.async_ = False

    def visit_AsyncFunctionDef(self, node):
        node = self.get_function_node(node)
        if node is not None:
            node.async_ = True

    def visit_ClassDef(self, node):
        self.defined_types.add(node.name)

        bases = []
        for n in node.bases:
            base_parts = []
            while True:
                if not isinstance(n, ast.Attribute):
                    base_parts.append(n.id)
                    break
                else:
                    base_parts.append(n.attr)
                n = n.value
            bases.append(".".join(base_parts[::-1]))
        self.required_types |= set(bases)

        signature_key = node.name
        if isinstance(self._parents[-1], ClassNode):
            signature_key = self._parents[-1].name + "." + node.name
        signature = self.signatures.get(signature_key)
        stub_node = ClassNode(node.name, bases=bases, signature=signature)
        self._parents[-1].add_child(stub_node)

        self._parents.append(stub_node)
        self.generic_visit(node)
        del self._parents[-1]

    # StubGenerator.analyze_types:: () -> Dict[str, Set[str]]
    def analyze_types(self):
        """Scan required types and determine type groups.

        :return: Report containing imported types and needed namespaces.
        :raise ValueError: When all needed types cannot be resolved.
        """
        report = {}

        needed_types = self.required_types - _BUILTIN_TYPES

        needed_types -= self.defined_types

        qualified_types = {name for name in needed_types if "." in name}
        needed_types -= qualified_types

        module_vars = {name for name in self.root.children if isinstance(name, VariableNode)}

        needed_modules = {
            name[: name.rfind(".")] for name in qualified_types if name not in module_vars
        }

        imported_names = {name.split("::")[0] for name in self.imported_names}
        imported_used = imported_names & (needed_types | needed_modules)
        if len(imported_used) > 0:
            report["imported"] = imported_used
            needed_types -= imported_used

        needed_modules -= imported_names
        if len(needed_modules) > 0:
            report["modules"] = needed_modules

        typing_mod = __import__("typing")
        typing_types = {name for name in needed_types if hasattr(typing_mod, name)}
        if len(typing_types) > 0:
            report["typing"] = typing_types
            needed_types -= typing_types

        if len(needed_types) > 0:
            raise ValueError("unresolved types: " + ", ".join(needed_types))
        return report

    # StubGenerator.print_stub:: () -> None
    def print_stub(self):
        """Print the stub code for this source."""
        types = self.analyze_types()

        typing_types = types.get("typing")
        if typing_types is not None:
            _print_import_from("typing", typing_types)

        imported_types = types.get("imported")
        if imported_types is not None:
            # preserve the import order in the source file
            for name in self.imported_names:
                if name.split("::")[0] in imported_types:
                    _print_import_from(self.imported_names[name], {name})

        needed_modules = types.get("modules")
        if needed_modules is not None:
            as_names = {n.split("::")[0]: n for n in self.imported_namespaces if "::" in n}
            for module_ in sorted(needed_modules):
                if module_ in as_names:
                    a, n = as_names[module_].split("::")
                    print("import " + n + " as " + a)
                else:
                    print("import " + module_)

        if len(self.aliases) > 0:
            for alias, signature in self.aliases.items():
                print("%s = %s" % (alias, signature))
            print()

        self.root.print_stub()


# get_stub:: (str, bool) -> str
def get_stub(source, *, generic=False):
    """Get the stub code for a source code.

    :param source: Source code to generate the stub for.
    :param generic: Whether to produce generic stubs.
    :return: Generated stub code.
    """
    generator = StubGenerator(source, generic=generic)
    out = StringIO()
    with redirect_stdout(out):
        generator.print_stub()
    return out.getvalue()


############################################################
# UTILITIES
############################################################


# get_mod_paths:: (str) -> Optional[Tuple[Path, Path]]
def get_mod_paths(mod_name):
    """Get source and output file paths of a module.

    :param mod_name: Name of module to get the paths for.
    :return: Path of source file and subpath in output directory,
        or ``None`` if module can not be found.
    """
    mod = get_loader(mod_name)
    if mod is None:
        return None

    source = getattr(mod, "path", None)  # for pypy3
    if (source is None) or (not source.endswith(".py")):
        return None

    subpath = Path(*mod_name.split("."))
    if source == "__init__.py":
        subpath = subpath.joinpath("__init__.py")
    return Path(source), subpath


# get_pkg_paths:: (str) -> List[Tuple[Path, Path]]
def get_pkg_paths(pkg_name):
    """Get all module paths in a package.

    :param pkg_name: Name of package to get the module paths for.
    :return: Paths of modules in package.
    """
    try:
        pkg = import_module(pkg_name)
    except ModuleNotFoundError:
        return []

    if not hasattr(pkg, "__path__"):
        mod_path = get_mod_paths(pkg_name)
        return [mod_path] if mod_path is not None else []

    paths = []
    for mod_info in walk_packages(pkg.__path__, pkg.__name__ + "."):
        mod_path = get_mod_paths(mod_info.name)
        if mod_path is not None:
            paths.append(mod_path)
    return paths


############################################################
# MAIN
############################################################


# _make_parser:: (str) -> ArgumentParser
def _make_parser(prog):
    parser = ArgumentParser(prog=prog)
    parser.add_argument("--version", action="version", version="%(prog)s " + __version__)
    parser.add_argument("files", nargs="*", help="generate stubs for given files")
    parser.add_argument(
        "-m",
        "--module",
        action="append",
        metavar="MODULE",
        dest="modules",
        default=[],
        help="generate stubs for given modules",
    )
    parser.add_argument(
        "-o", "--output", metavar="PATH", dest="out_dir", help="change the output directory"
    )
    parser.add_argument(
        "--generic", action="store_true", default=False, help="generate generic stubs"
    )
    return parser


# _collect_sources:: (List[str], List[str]) -> List[Tuple[Path, Path]]
def _collect_sources(files, modules):
    """Collect the source file paths."""
    sources = []
    for path in files:
        paths = Path(path).glob("**/*.py") if Path(path).is_dir() else [Path(path)]
        for source in paths:
            if str(source).startswith(os.path.pardir):
                source = source.absolute().resolve()
            sources.append((source, source))

    for mod_name in modules:
        sources.extend(get_pkg_paths(mod_name))
    return sources


# run:: (Optional[List[str]]) -> None
def run(argv=None):
    parser = _make_parser("pygenstub")

    argv = argv if argv is not None else sys.argv
    arguments = parser.parse_args(argv[1:])

    out_dir = arguments.out_dir if arguments.out_dir is not None else ""

    if (out_dir == "") and (len(arguments.modules) > 0):
        print("output directory is required when generating stubs for modules", file=sys.stderr)
        sys.exit(1)

    sources = _collect_sources(arguments.files, arguments.modules)
    for source, subpath in sources:
        if (out_dir != "") and subpath.is_absolute():
            subpath = subpath.relative_to(subpath.root)
        stub = Path(out_dir, subpath.with_suffix(".pyi"))
        code = source.read_text(encoding="utf-8")
        stub_code = get_stub(code, generic=arguments.generic)
        if stub_code != "":
            if not stub.parent.exists():
                stub.parent.mkdir(parents=True)
            stub.write_text("# %s\n\n%s" % (_EDIT_WARNING, stub_code), encoding="utf-8")


if __name__ == "__main__":
    run()
