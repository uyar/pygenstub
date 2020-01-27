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

"""A utility for generating stub files from docstrings."""

import ast
import builtins
import inspect
import logging
import os
import re
import sys
import textwrap
from argparse import ArgumentParser
from bisect import bisect
from importlib import import_module
from io import StringIO
from pathlib import Path
from pkgutil import get_loader, walk_packages

from docutils.core import publish_doctree


__version__ = "2.0.0b1"  # sig: str


_BUILTIN_TYPES = {k for k, t in builtins.__dict__.items() if isinstance(t, type)}
_BUILTIN_TYPES.add("None")

SIG_FIELD = "sig"
_SIG_COMMENT = "# sig:"

_SUPPORTED_DECORATORS = {"property", "staticmethod", "classmethod"}

MAX_LINE_LENGTH = 79
INDENT = 4 * " "

_EDIT_WARNING = "THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY."

_RE_QUALIFIED_TYPES = re.compile(r"\w+(?:\.\w+)*")
_RE_COMMENT_IN_STRING = re.compile(r"""['"]\s*%(text)s\s*.*['"]""" % {"text": _SIG_COMMENT})
_RE_SIG_ARROW = re.compile(r"\s+->\s+")
_RE_SIG_ALIAS = re.compile(r"\s*#\s+sigalias:\s+([^\s]*)\s+=\s+([^\s]*)\s*$")


_logger = logging.getLogger(__name__)


############################################################
# SIGNATURE PROCESSING
############################################################


def extract_signature(docstring):
    """Extract the signature from a docstring.

    :sig: (str) -> Optional[str]
    :param docstring: Docstring to extract the signature from.
    :return: Signature, or ``None`` if no signature found.
    :raise ValueError: When docstring contains multiple signature fields.
    """
    root = publish_doctree(docstring, settings_overrides={"report_level": 5})
    sig_fields = [
        field
        for node in root.children
        if node.tagname == "field_list"
        for field in node.children
        for field_info in field.children
        if (field_info.tagname == "field_name") and (field_info.rawsource == SIG_FIELD)
    ]
    if len(sig_fields) == 0:
        return None
    if len(sig_fields) > 1:
        raise ValueError("multiple signature fields")
    return "".join(f.rawsource for f in sig_fields[0].children if f.tagname == "field_body")


def _split_types(decl):
    """Split a parameter types declaration into individual types.

    :sig: (str) -> List[str]
    :param decl: Parameter types declaration (excluding the parentheses).
    :return: List of individual parameter types.
    """
    if decl == "":
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for i, char in enumerate(decl):
        if (char == ",") and (bracket_depth == 0):
            commas.append(i)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1

    types = []
    last_i = 0
    for i in commas:
        types.append(decl[last_i:i].strip())
        last_i = i + 1
    else:
        types.append(decl[last_i:].strip())
    return types


def parse_signature(signature):
    """Parse input and return parameter types from a signature.

    This will also collect the types that are required by any of the input
    and return types.

    :sig: (str) -> Tuple[List[str], str, Set[str]]
    :param signature: Signature to parse.
    :return: Input parameter types, return type, and all required types.
    :raise ValueError: When signature cannot be correctly parsed.
    """
    sig_parts = _RE_SIG_ARROW.split(signature)
    if len(sig_parts) > 2:
        raise ValueError("multiple arrows in signature")
    if len(sig_parts) == 1:
        # signature comment: no parameters, treat variable type as return type
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
# AST PROCESSING
############################################################


class StubNode:
    """A node in a stub tree."""

    def __init__(self):
        """Initialize this stub node.

        :sig: () -> None
        """
        self.parent = None  # sig: Optional[StubNode]
        """Parent node of this node."""

        self.children = []  # sig: List[StubNode]
        """Child nodes of this node."""

    def add_child(self, node):
        """Add a child node to this node.

        :sig: (StubNode) -> None
        :param node: Node to add.
        """
        self.children.append(node)
        node.parent = self

    def get_code(self):
        """Get the stub code for this node.

        The stub code for a node consists of the type annotations of its variables,
        followed by the prototypes of its functions/methods and classes.

        :sig: () -> List[str]
        :return: Lines of stub code for this node.
        """
        stub = []
        variables = [n for n in self.children if isinstance(n, VariableNode)]
        nonvariables = [n for n in self.children if not isinstance(n, VariableNode)]
        for child in variables:
            stub.extend(child.get_code())
        if (
            (len(variables) > 0)
            and (len(nonvariables) > 0)
            and (not isinstance(self, ClassNode))
        ):
            stub.append("")
        for child in nonvariables:
            stub.extend(child.get_code())
        return stub


class VariableNode(StubNode):
    """A node representing an assignment in a stub tree."""

    def __init__(self, name, type_):
        """Initialize this variable node.

        :sig: (str, str) -> None
        :param name: Name of variable that is being assigned to.
        :param type_: Type of variable.
        """
        super().__init__()
        self.name = name  # sig: str
        self.type_ = type_  # sig: str

    def get_code(self):
        """Get the type annotation for this variable.

        :sig: () -> List[str]
        :return: Lines of stub code for this variable.
        """
        return ["%(n)s = ...  # type: %(t)s" % {"n": self.name, "t": self.type_}]


class FunctionNode(StubNode):
    """A node representing a function in a stub tree."""

    def __init__(self, name, parameters, rtype, *, decorators=None):
        """Initialize this function node.

        The parameters have to given as a list of triples where each item specifies
        the name of the parameter, its type, and whether it has a default value or not.

        :sig: (str, Sequence[Tuple[str, str, bool]], str, Optional[Sequence[str]]) -> None
        :param name: Name of function.
        :param parameters: List of parameter triples (name, type, has_default).
        :param rtype: Type of return value.
        :param decorators: Decorators of function.
        """
        super().__init__()
        self.name = name  # sig: str
        self.async_ = False  # sig: bool
        self.parameters = parameters  # sig: Sequence[Tuple[str, str, bool]]
        self.rtype = rtype  # sig: str
        self.decorators = decorators if decorators is not None else []  # sig: Sequence[str]

    def get_code(self):
        """Get the stub code for this function.

        :sig: () -> List[str]
        :return: Lines of stub code for this function.
        """
        stub = []

        for deco in self.decorators:
            if (deco in _SUPPORTED_DECORATORS) or deco.endswith(".setter"):
                stub.append("@" + deco)

        parameters = []
        for name, type_, has_default in self.parameters:
            decl = "%(n)s%(t)s%(d)s" % {
                "n": name,
                "t": ": " + type_ if type_ else "",
                "d": " = ..." if has_default else "",
            }
            parameters.append(decl)

        slots = {
            "a": "async " if self.async_ else "",
            "n": self.name,
            "p": ", ".join(parameters),
            "r": self.rtype,
        }

        prototype = "%(a)sdef %(n)s(%(p)s) -> %(r)s: ..." % slots
        if len(prototype) <= MAX_LINE_LENGTH:
            stub.append(prototype)
        elif len(INDENT + slots["p"]) <= MAX_LINE_LENGTH:
            stub.append("%(a)sdef %(n)s(" % slots)
            stub.append(INDENT + slots["p"])
            stub.append(") -> %(r)s: ..." % slots)
        else:
            stub.append("%(a)sdef %(n)s(" % slots)
            for param in parameters:
                stub.append(INDENT + param + ",")
            stub.append(") -> %(r)s: ..." % slots)

        return stub


class ClassNode(StubNode):
    """A node representing a class in a stub tree."""

    def __init__(self, name, *, bases, signature=None):
        """Initialize this class node.

        :sig: (str, Sequence[str], Optional[str]) -> None
        :param name: Name of class.
        :param bases: Base classes of class.
        :param signature: Signature of class, to be used in __init__ method.
        """
        super().__init__()
        self.name = name  # sig: str
        self.bases = bases  # sig: Sequence[str]
        self.signature = signature  # sig: Optional[str]

    def get_code(self):
        """Get the stub code for this class.

        :sig: () -> List[str]
        :return: Lines of stub code for this class.
        """
        stub = []
        bases = ("(" + ", ".join(self.bases) + ")") if len(self.bases) > 0 else ""
        slots = {"n": self.name, "b": bases}
        if len(self.children) == 0:
            stub.append("class %(n)s%(b)s: ..." % slots)
        else:
            stub.append("class %(n)s%(b)s:" % slots)
            super_code = super().get_code()
            for line in super_code:
                stub.append(INDENT + line)
        return stub


def get_aliases(lines):
    """Get the type aliases in the source.

    :sig: (Sequence[str]) -> Dict[str, str]
    :param lines: Lines of the source code.
    :return: Aliases and their their definitions.
    """
    aliases = {}
    for line in lines:
        match = _RE_SIG_ALIAS.match(line)
        if match:
            alias, signature = match.groups()
            aliases[alias] = signature
    return aliases


class StubGenerator(ast.NodeVisitor):
    """A transformer that generates stub declarations from a source code."""

    def __init__(self, source, *, generic=False):
        """Initialize this stub generator.

        :sig: (str, bool) -> None
        :param source: Source code to generate the stub for.
        :param generic: Whether to produce generic stubs.
        """
        self.root = StubNode()  # sig: StubNode

        self.generic = generic  # sig: bool

        self.imported_namespaces = {}  # sig: Dict[str, str]
        self.imported_names = {}  # sig: Dict[str, str]
        self.defined_types = set()  # sig: Set[str]
        self.required_types = set()  # sig: Set[str]
        self.aliases = {}  # sig: Dict[str, str]

        self._parents = [self.root]  # sig: List[StubNode]
        self._code_lines = source.splitlines()  # sig: List[str]

        self.collect_aliases()

        ast_tree = ast.parse(source)
        self.visit(ast_tree)

    def collect_aliases(self):
        """Collect the type aliases in the source.

        :sig: () -> None
        """
        self.aliases = get_aliases(self._code_lines)
        for alias, signature in self.aliases.items():
            _, _, requires = parse_signature(signature)
            self.required_types |= requires
            self.defined_types |= {alias}

    def visit_Import(self, node):
        """Visit an import node."""
        line = self._code_lines[node.lineno - 1]
        module_name = line.split("import")[0].strip()
        for name in node.names:
            imported_name = name.name
            if name.asname:
                imported_name = name.asname + "::" + imported_name
            self.imported_namespaces[imported_name] = module_name

    def visit_ImportFrom(self, node):
        """Visit an from-import node."""
        line = self._code_lines[node.lineno - 1]
        module_name = line.split("from")[1].split("import")[0].strip()
        for name in node.names:
            imported_name = name.name
            if name.asname:
                imported_name = name.asname + "::" + imported_name
            self.imported_names[imported_name] = module_name

    def visit_Assign(self, node):
        """Visit an assignment node."""
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

    def get_function_node(self, node):
        """Process a function node.

        :sig: (Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> FunctionNode
        :param node: Node to process.
        :return: Generated function node in stub tree.
        """
        decorators = []
        for d in node.decorator_list:
            if hasattr(d, "id"):
                decorators.append(d.id)
            elif hasattr(d, "func"):
                decorators.append(d.func.id)
            elif hasattr(d, "value"):
                decorators.append(d.value.id + "." + d.attr)

        docstring = ast.get_docstring(node)
        signature = extract_signature(docstring) if docstring is not None else None

        if signature is None:
            parent = self._parents[-1]
            if isinstance(parent, ClassNode) and (node.name == "__init__"):
                signature = parent.signature

        if (signature is None) and (not self.generic):
            return None

        param_names = [arg.arg for arg in node.args.args]
        n_args = len(param_names)

        if signature is None:
            param_types, rtype, requires = ["Any"] * n_args, "Any", {"Any"}
        else:
            _logger.debug("parsing signature for %s", node.name)
            param_types, rtype, requires = parse_signature(signature)

        # TODO: only in classes
        if ((n_args > 0) and (param_names[0] == "self")) or (
            (n_args > 0) and (param_names[0] == "cls") and ("classmethod" in decorators)
        ):
            if signature is None:
                param_types[0] = ""
            else:
                param_types.insert(0, "")

        _logger.debug("parameter types: %s", param_types)
        _logger.debug("return type: %s", rtype)
        _logger.debug("required types: %s", requires)

        self.required_types |= requires

        if node.args.vararg is not None:
            param_names.append("*" + node.args.vararg.arg)
            param_types.append("")

        if node.args.kwarg is not None:
            param_names.append("**" + node.args.kwarg.arg)
            param_types.append("")

        kwonly_args = getattr(node.args, "kwonlyargs", [])
        if len(kwonly_args) > 0:
            param_names.extend([arg.arg for arg in kwonly_args])
            if signature is None:
                param_types.extend(["Any"] * len(kwonly_args))

        if len(param_types) != len(param_names):
            raise ValueError("Parameter names and types don't match: " + node.name)

        param_locs = [(a.lineno, a.col_offset) for a in (node.args.args + kwonly_args)]
        param_defaults = {
            bisect(param_locs, (d.lineno, d.col_offset)) - 1 for d in node.args.defaults
        }

        kwonly_defaults = getattr(node.args, "kw_defaults", [])
        for i, d in enumerate(kwonly_defaults):
            if d is not None:
                param_defaults.add(n_args + i)

        params = [
            (name, type_, i in param_defaults)
            for i, (name, type_) in enumerate(zip(param_names, param_types))
        ]

        if len(kwonly_args) > 0:
            params.insert(n_args, ("*", "", False))

        stub_node = FunctionNode(
            node.name, parameters=params, rtype=rtype, decorators=decorators
        )
        self._parents[-1].add_child(stub_node)

        self._parents.append(stub_node)
        self.generic_visit(node)
        del self._parents[-1]
        return stub_node

    def visit_FunctionDef(self, node):
        """Visit a function node."""
        node = self.get_function_node(node)
        if node is not None:
            node._async = False

    def visit_AsyncFunctionDef(self, node):
        """Visit an async function node."""
        node = self.get_function_node(node)
        if node is not None:
            node._async = True

    def visit_ClassDef(self, node):
        """Visit a class node."""
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

        docstring = ast.get_docstring(node)
        signature = extract_signature(docstring) if docstring is not None else None
        stub_node = ClassNode(node.name, bases=bases, signature=signature)
        self._parents[-1].add_child(stub_node)

        self._parents.append(stub_node)
        self.generic_visit(node)
        del self._parents[-1]

    @staticmethod
    def generate_import_from(module_, names):
        """Generate an import line.

        :sig: (str, Set[str]) -> str
        :param module_: Name of module to import the names from.
        :param names: Names to import.
        :return: Import line in stub code.
        """
        regular_names = [n for n in names if "::" not in n]
        as_names = [n for n in names if "::" in n]

        line = ""
        if len(regular_names) > 0:
            slots = {"m": module_, "n": ", ".join(sorted(regular_names))}
            line = "from %(m)s import %(n)s" % slots
            if len(line) > MAX_LINE_LENGTH:
                slots["n"] = INDENT + (",\n" + INDENT).join(sorted(regular_names)) + ","
                line = "from %(m)s import (\n%(n)s\n)" % slots
            if len(as_names) > 0:
                line += "\n"

        for as_name in as_names:
            a, n = as_name.split("::")
            line += "from %(m)s import %(n)s as %(a)s" % {"m": module_, "n": n, "a": a}
        return line

    def analyze_types(self):
        """Scan required types and determine type groups.

        :sig: () -> Dict[str, Set[str]]
        :return: Report containing imported types and needed namespaces.
        :raise ValueError: When all needed types cannot be resolved.
        """
        report = {}
        needed_types = self.required_types - _BUILTIN_TYPES

        _logger.debug("defined types: %s", self.defined_types)
        needed_types -= self.defined_types

        qualified_types = {name for name in needed_types if "." in name}
        _logger.debug("qualified types: %s", qualified_types)
        needed_types -= qualified_types

        module_vars = {name for name in self.root.children if isinstance(name, VariableNode)}
        _logger.debug("module variables: %s", module_vars)

        needed_modules = {
            name[: name.rfind(".")] for name in qualified_types if name not in module_vars
        }

        imported_names = {name.split("::")[0] for name in self.imported_names}
        imported_used = imported_names & (needed_types | needed_modules)
        if len(imported_used) > 0:
            _logger.debug("used imported types: %s", imported_used)
            report["imported"] = imported_used
            needed_types -= imported_used

        needed_modules -= imported_names
        if len(needed_modules) > 0:
            _logger.debug("needed modules: %s", needed_modules)
            report["modules"] = needed_modules

        typing_mod = __import__("typing")
        typing_types = {name for name in needed_types if hasattr(typing_mod, name)}
        if len(typing_types) > 0:
            _logger.debug("types from typing module: %s", typing_types)
            report["typing"] = typing_types
            needed_types -= typing_types

        if len(needed_types) > 0:
            raise ValueError("unresolved types: " + ", ".join(needed_types))
        return report

    def generate_stub(self):
        """Generate the stub code for this source.

        :sig: () -> str
        :return: Generated stub code.
        """
        types = self.analyze_types()

        out = StringIO()
        started = False

        typing_types = types.get("typing")
        if typing_types is not None:
            line = self.generate_import_from("typing", typing_types)
            out.write(line + "\n")
            started = True

        imported_types = types.get("imported")
        if imported_types is not None:
            if started:
                out.write("\n")
            # preserve the import order in the source file
            for name in self.imported_names:
                if name.split("::")[0] in imported_types:
                    line = self.generate_import_from(self.imported_names[name], {name})
                    out.write(line + "\n")
            started = True

        needed_modules = types.get("modules")
        if needed_modules is not None:
            if started:
                out.write("\n")
            as_names = {n.split("::")[0]: n for n in self.imported_namespaces if "::" in n}
            for module_ in sorted(needed_modules):
                if module_ in as_names:
                    a, n = as_names[module_].split("::")
                    out.write("import " + n + " as " + a + "\n")
                else:
                    out.write("import " + module_ + "\n")
            started = True

        if len(self.aliases) > 0:
            if started:
                out.write("\n")
            for alias, signature in self.aliases.items():
                out.write("%s = %s\n" % (alias, signature))
            started = True

        if started:
            out.write("\n")
        stub_lines = self.root.get_code()
        n_lines = len(stub_lines)
        for line_no in range(n_lines):
            prev_line = stub_lines[line_no - 1] if line_no > 0 else None
            line = stub_lines[line_no]
            next_line = stub_lines[line_no + 1] if line_no < (n_lines - 1) else None
            if (
                line.startswith("class ")
                and (prev_line is not None)
                and (
                    (not prev_line.startswith("class "))
                    or (next_line and next_line.startswith(" "))
                )
            ):
                out.write("\n")
            if (
                line.startswith("def ")
                and (prev_line is not None)
                and (prev_line.startswith((" ", "class ")))
            ):
                out.write("\n")
            out.write(line + "\n")
            line_no += 1
        return out.getvalue()


def get_stub(source, *, generic=False):
    """Get the stub code for a source code.

    :sig: (str, bool) -> str
    :param source: Source code to generate the stub for.
    :param generic: Whether to produce generic stubs.
    :return: Generated stub code.
    """
    generator = StubGenerator(source, generic=generic)
    stub = generator.generate_stub()
    return stub


############################################################
# UTILITIES
############################################################


def get_mod_paths(mod_name):
    """Get source and output file paths of a module.

    :sig: (str) -> Tuple[Path, Path]
    :param mod_name: Name of module to get the paths for.
    :return: Path of source file and subpath in output directory,
        or ``None`` if module can not be found.
    """
    mod = get_loader(mod_name)
    if mod is None:
        _logger.debug("failed to find module: %s", mod_name)
        return None

    source = mod.path if hasattr(mod, "path") else None  # for pypy3
    if (source is None) or (not source.endswith(".py")):
        _logger.debug("failed to find python source for module: %s", mod_name)
        return None

    subpath = Path(*mod_name.split("."))
    if source == "__init__.py":
        subpath = subpath.joinpath("__init__.py")
    return Path(source), subpath


def get_pkg_paths(pkg_name):
    """Get all module paths in a package.

    :sig: (str) -> List[Tuple[Path, Path]]
    :param pkg_name: Name of package to get the module paths for.
    :return: Paths of modules in package.
    """
    try:
        pkg = import_module(pkg_name)
    except ModuleNotFoundError:
        _logger.debug("failed to load module: %s", pkg_name)
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
# SPHINX
############################################################


def process_docstring(app, what, name, obj, options, lines):
    """Modify the docstring before generating documentation.

    This will insert type declarations for parameters and return type
    into the docstring, and remove the signature field so that it will
    be excluded from the generated document.
    """
    aliases = getattr(app, "_sigaliases", None)
    if aliases is None:
        if what == "module":
            aliases = get_aliases(inspect.getsource(obj).splitlines())
            app._sigaliases = aliases

    sig_marker = ":" + SIG_FIELD + ":"
    is_class = what in ("class", "exception")

    signature = extract_signature("\n".join(lines))
    if signature is None:
        if not is_class:
            return

        init_method = getattr(obj, "__init__")
        init_doc = init_method.__doc__
        init_lines = init_doc.splitlines()[1:]
        if len(init_lines) > 1:
            init_doc = textwrap.dedent("\n".join(init_lines[1:]))
            init_lines = init_doc.splitlines()
        if sig_marker not in init_doc:
            return

        sig_started = False
        for line in init_lines:
            if line.lstrip().startswith(sig_marker):
                sig_started = True
            if sig_started:
                lines.append(line)
        signature = extract_signature("\n".join(lines))

    if is_class:
        obj = init_method

    param_types, rtype, _ = parse_signature(signature)
    param_names = [p for p in inspect.signature(obj).parameters]

    if is_class and (param_names[0] == "self"):
        del param_names[0]

    # if something goes wrong, don't insert parameter types
    if len(param_names) == len(param_types):
        for name, type_ in zip(param_names, param_types):
            find = ":param %(name)s:" % {"name": name}
            alias = aliases.get(type_)
            if alias is not None:
                type_ = "*%(type)s* :sup:`%(alias)s`" % {"type": type_, "alias": alias}
            for i, line in enumerate(lines):
                if line.startswith(find):
                    lines.insert(i, ":type %(name)s: %(type)s" % {"name": name, "type": type_})
                    break

    if not is_class:
        for i, line in enumerate(lines):
            if line.startswith((":return:", ":returns:")):
                lines.insert(i, ":rtype: " + rtype)
                break

    # remove the signature field
    sig_start = 0
    while sig_start < len(lines):
        if lines[sig_start].startswith(sig_marker):
            break
        sig_start += 1
    sig_end = sig_start + 1
    while sig_end < len(lines):
        if (not lines[sig_end]) or (lines[sig_end][0] != " "):
            break
        sig_end += 1
    for i in reversed(range(sig_start, sig_end)):
        del lines[i]


def setup(app):
    """Register to Sphinx."""
    app.connect("autodoc-process-docstring", process_docstring)
    return {"version": __version__}


############################################################
# MAIN
############################################################


def _make_parser(prog):
    """Create a parser for command line arguments.

    :sig: (str) -> ArgumentParser
    """
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
    parser.add_argument("--debug", action="store_true", help="enable debug messages")
    return parser


def _collect_sources(files, modules):
    """Collect the source file paths.

    :sig: (List[str], List[str]) -> List[Path]
    """
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


def run(argv=None):
    """Start the command line interface.

    :sig: (Optional[List[str]]) -> None
    :param argv: Command line arguments.
    """
    parser = _make_parser("pygenstub")

    argv = argv if argv is not None else sys.argv
    arguments = parser.parse_args(argv[1:])

    # set debug mode
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)
        _logger.debug("running in debug mode")

    out_dir = arguments.out_dir if arguments.out_dir is not None else ""

    if (out_dir == "") and (len(arguments.modules) > 0):
        print("output directory is required when generating stubs for modules", file=sys.stderr)
        sys.exit(1)

    sources = _collect_sources(arguments.files, arguments.modules)
    for source, subpath in sources:
        if (out_dir != "") and subpath.is_absolute():
            subpath = subpath.relative_to(subpath.root)
        stub = Path(out_dir, subpath.with_suffix(".pyi"))
        _logger.info("generating stub for %s to path %s", source, stub)
        code = source.read_text(encoding="utf-8")
        stub_code = get_stub(code, generic=arguments.generic)
        if stub_code != "":
            if not stub.parent.exists():
                stub.parent.mkdir(parents=True)
            stub.write_text("# %s\n\n%s" % (_EDIT_WARNING, stub_code), encoding="utf-8")


if __name__ == "__main__":
    run()
