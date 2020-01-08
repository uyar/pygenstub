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

from __future__ import absolute_import, print_function, unicode_literals

import ast
import inspect
import logging
import os
import re
import sys
import textwrap
from argparse import ArgumentParser
from bisect import bisect
from collections import OrderedDict
from importlib import import_module
from io import StringIO
from pkgutil import get_loader, walk_packages

from docutils.core import publish_doctree


__version__ = "1.4.0"


PY3 = sys.version_info >= (3, 0)

if not PY3:
    import __builtin__ as builtins
    from pathlib2 import Path
else:
    import builtins
    from pathlib import Path


# sigalias: Document = docutils.nodes.document


BUILTIN_TYPES = {k for k, t in builtins.__dict__.items() if isinstance(t, type)}
BUILTIN_TYPES.add("None")

SIG_FIELD = "sig"
SIG_COMMENT = "# sig:"
SIG_ALIAS = "# sigalias:"

DECORATORS = {"property", "staticmethod", "classmethod"}

LINE_LENGTH_LIMIT = 79
INDENT = 4 * " "

EDIT_WARNING = "THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY."

_RE_QUALIFIED_TYPES = re.compile(r"\w+(?:\.\w+)*")
_RE_COMMENT_IN_STRING = re.compile(r"""['"]\s*%(text)s\s*.*['"]""" % {"text": SIG_COMMENT})


_logger = logging.getLogger(__name__)


def get_fields(node, fields_tag="field_list"):
    """Get the field names and their values from a node.

    :sig: (Document, str) -> Dict[str, str]
    :param node: Node to get the fields from.
    :param fields_tag: Tag of child node that contains the fields.
    :return: Names and values of fields.
    """
    fields_nodes = [c for c in node.children if c.tagname == fields_tag]
    if len(fields_nodes) == 0:
        return {}
    assert len(fields_nodes) == 1, "multiple nodes with tag " + fields_tag
    fields_node = fields_nodes[0]
    fields = [
        {f.tagname: f.rawsource.strip() for f in n.children}
        for n in fields_node.children
        if n.tagname == "field"
    ]
    return {f["field_name"]: f["field_body"] for f in fields}


def extract_signature(docstring):
    """Extract the signature from a docstring.

    :sig: (str) -> Optional[str]
    :param docstring: Docstring to extract the signature from.
    :return: Extracted signature, or ``None`` if there's no signature.
    """
    root = publish_doctree(docstring, settings_overrides={"report_level": 5})
    fields = get_fields(root)
    return fields.get(SIG_FIELD)


def get_signature(node):
    """Get the signature of a function or a class.

    :sig: (Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]) -> Optional[str]
    :param node: Node to get the signature from.
    :return: Value of signature field in node docstring, or ``None`` if there's no signature.
    """
    docstring = ast.get_docstring(node)
    if docstring is None:
        return None
    return extract_signature(docstring)


def split_parameter_types(parameters):
    """Split a parameter types declaration into individual types.

    The input is the left hand side of a signature (the part before the arrow),
    excluding the parentheses.

    :sig: (str) -> List[str]
    :param parameters: Comma separated parameter types.
    :return: Parameter types.
    """
    if parameters == "":
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for i, char in enumerate(parameters):
        if (char == ",") and (bracket_depth == 0):
            commas.append(i)
        elif char == "[":
            bracket_depth += 1
        elif char == "]":
            bracket_depth -= 1

    types = []
    last_i = 0
    for i in commas:
        types.append(parameters[last_i:i].strip())
        last_i = i + 1
    else:
        types.append(parameters[last_i:].strip())
    return types


def parse_signature(signature):
    """Parse a signature into its input and return parameter types.

    This will also collect the types that are required by any of the input
    and return types.

    :sig: (str) -> Tuple[List[str], str, Set[str]]
    :param signature: Signature to parse.
    :return: Input parameter types, return type, and all required types.
    """
    if " -> " not in signature:
        # signature comment: no parameters, treat variable type as return type
        param_types, return_type = None, signature.strip()
    else:
        lhs, return_type = [s.strip() for s in signature.split(" -> ")]
        csv = lhs[1:-1].strip()  # remove the parentheses around the parameter type list
        param_types = split_parameter_types(csv)
    requires = set(_RE_QUALIFIED_TYPES.findall(signature))
    return param_types, return_type, requires


class StubNode:
    """A node in a stub tree."""

    def __init__(self):
        """Initialize this stub node.

        :sig: () -> None
        """
        self.variables = []  # sig: List[VariableNode]
        self.variable_names = set()  # sig: Set[str]
        self.children = []  # sig: List[Union[FunctionNode, ClassNode]]
        self.parent = None  # sig: Optional[StubNode]

    def add_variable(self, node):
        """Add a variable node to this node.

        :sig: (VariableNode) -> None
        :param node: Variable node to add.
        """
        if node.name not in self.variable_names:
            self.variables.append(node)
            self.variable_names.add(node.name)
            node.parent = self

    def add_child(self, node):
        """Add a function/method or class node to this node.

        :sig: (Union[FunctionNode, ClassNode]) -> None
        :param node: Function or class node to add.
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
        for child in self.variables:
            stub.extend(child.get_code())
        if (
            (len(self.variables) > 0)
            and (len(self.children) > 0)
            and (not isinstance(self, ClassNode))
        ):
            stub.append("")
        for child in self.children:
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
        if not PY3:
            StubNode.__init__(self)
        else:
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

    def __init__(self, name, parameters, rtype, decorators=None):
        """Initialize this function node.

        The parameters have to given as a list of triples where each item specifies
        the name of the parameter, its type, and whether it has a default value or not.

        :sig: (str, Sequence[Tuple[str, str, bool]], str, Optional[Sequence[str]]) -> None
        :param name: Name of function.
        :param parameters: List of parameter triples (name, type, has_default).
        :param rtype: Type of return value.
        :param decorators: Decorators of function.
        """
        if not PY3:
            StubNode.__init__(self)
        else:
            super().__init__()
        self.name = name  # sig: str
        self.parameters = parameters  # sig: Sequence[Tuple[str, str, bool]]
        self.rtype = rtype  # sig: str
        self.decorators = decorators if decorators is not None else []  # sig: Sequence[str]

        self._async = False  # sig: bool

    def get_code(self):
        """Get the stub code for this function.

        :sig: () -> List[str]
        :return: Lines of stub code for this function.
        """
        stub = []

        for deco in self.decorators:
            if (deco in DECORATORS) or deco.endswith(".setter"):
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
            "a": "async " if self._async else "",
            "n": self.name,
            "p": ", ".join(parameters),
            "r": self.rtype,
        }

        prototype = "%(a)sdef %(n)s(%(p)s) -> %(r)s: ..." % slots
        if len(prototype) <= LINE_LENGTH_LIMIT:
            stub.append(prototype)
        elif len(INDENT + slots["p"]) <= LINE_LENGTH_LIMIT:
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

    def __init__(self, name, bases, signature=None):
        """Initialize this class node.

        :sig: (str, Sequence[str], Optional[str]) -> None
        :param name: Name of class.
        :param bases: Base classes of class.
        :param signature: Signature of class, to be used in __init__ method.
        """
        if not PY3:
            StubNode.__init__(self)
        else:
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
        if (len(self.children) == 0) and (len(self.variables) == 0):
            stub.append("class %(n)s%(b)s: ..." % slots)
        else:
            stub.append("class %(n)s%(b)s:" % slots)
            super_code = super().get_code() if PY3 else StubNode.get_code(self)
            for line in super_code:
                stub.append(INDENT + line)
        return stub


def get_aliases(lines):
    """Get the type aliases in the source.

    :sig: (Sequence[str]) -> OrderedDict[str, str]
    :param lines: Lines of the source code.
    :return: Aliases and their their definitions.
    """
    aliases = OrderedDict()
    for line in lines:
        line = line.strip()
        if len(line) > 0 and line.startswith(SIG_ALIAS):
            _, content = line.split(SIG_ALIAS)
            alias, signature = [t.strip() for t in content.split("=")]
            aliases[alias] = signature
    return aliases


class StubGenerator(ast.NodeVisitor):
    """A transformer that generates stub declarations from a source code."""

    def __init__(self, source, generic=False):
        """Initialize this stub generator.

        :sig: (str, bool) -> None
        :param source: Source code to generate the stub for.
        :param generic: Whether to produce generic stubs.
        """
        self.root = StubNode()  # sig: StubNode

        self.generic = generic  # sig: bool

        self.imported_namespaces = OrderedDict()  # sig: OrderedDict[str, str]
        self.imported_names = OrderedDict()  # sig: OrderedDict[str, str]
        self.defined_types = set()  # sig: Set[str]
        self.required_types = set()  # sig: Set[str]
        self.aliases = OrderedDict()  # sig: OrderedDict[str, str]

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
        if SIG_COMMENT in line:
            line = _RE_COMMENT_IN_STRING.sub("", line)

        if (SIG_COMMENT not in line) and (not self.generic):
            return

        if SIG_COMMENT in line:
            _, signature = line.split(SIG_COMMENT)
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
                p.add_variable(stub_node)

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

        signature = get_signature(node)

        if signature is None:
            parent = self._parents[-1]
            if isinstance(parent, ClassNode) and (node.name == "__init__"):
                signature = parent.signature

        if (signature is None) and (not self.generic):
            return None

        param_names = [arg.arg if PY3 else arg.id for arg in node.args.args]
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
            param_names.append("*" + (node.args.vararg.arg if PY3 else node.args.vararg))
            param_types.append("")

        if node.args.kwarg is not None:
            param_names.append("**" + (node.args.kwarg.arg if PY3 else node.args.kwarg))
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

        signature = get_signature(node)
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
            if len(line) > LINE_LENGTH_LIMIT:
                slots["n"] = INDENT + (",\n" + INDENT).join(sorted(regular_names)) + ","
                line = "from %(m)s import (\n%(n)s\n)" % slots
            if len(as_names) > 0:
                line += "\n"

        for as_name in as_names:
            a, n = as_name.split("::")
            line += "from %(m)s import %(n)s as %(a)s" % {"m": module_, "n": n, "a": a}
        return line

    def generate_stub(self):
        """Generate the stub code for this source.

        :sig: () -> str
        :return: Generated stub code.
        """
        needed_types = self.required_types - BUILTIN_TYPES

        needed_types -= self.defined_types
        _logger.debug("defined types: %s", self.defined_types)

        module_vars = {v.name for v in self.root.variables}
        _logger.debug("module variables: %s", module_vars)

        qualified_types = {n for n in needed_types if "." in n}
        qualified_namespaces = {".".join(n.split(".")[:-1]) for n in qualified_types}

        needed_namespaces = qualified_namespaces - module_vars
        needed_types -= qualified_types
        _logger.debug("needed namespaces: %s", needed_namespaces)

        imported_names = {n.split("::")[0] for n in self.imported_names}
        imported_types = imported_names & (needed_types | needed_namespaces)
        needed_types -= imported_types
        needed_namespaces -= imported_names
        _logger.debug("used imported types: %s", imported_types)

        try:
            typing_mod = __import__("typing")
            typing_types = {n for n in needed_types if hasattr(typing_mod, n)}
            needed_types -= typing_types
            _logger.debug("types from typing module: %s", typing_types)
        except ImportError:
            typing_types = set()
            _logger.warn("typing module not installed")

        if len(needed_types) > 0:
            raise ValueError("Unknown types: " + ", ".join(needed_types))

        out = StringIO()
        started = False

        if len(typing_types) > 0:
            line = self.generate_import_from("typing", typing_types)
            out.write(line + "\n")
            started = True

        if len(imported_types) > 0:
            if started:
                out.write("\n")
            # preserve the import order in the source file
            for name in self.imported_names:
                if name.split("::")[0] in imported_types:
                    line = self.generate_import_from(self.imported_names[name], {name})
                    out.write(line + "\n")
            started = True

        if len(needed_namespaces) > 0:
            if started:
                out.write("\n")
            as_names = {n.split("::")[0]: n for n in self.imported_namespaces if "::" in n}
            for module_ in sorted(needed_namespaces):
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


def get_stub(source, generic=False):
    """Get the stub code for a source code.

    :sig: (str, bool) -> str
    :param source: Source code to generate the stub for.
    :param generic: Whether to produce generic stubs.
    :return: Generated stub code.
    """
    generator = StubGenerator(source, generic=generic)
    stub = generator.generate_stub()
    return stub


def get_mod_paths(mod_name, out_dir):
    """Get source and stub paths for a module."""
    paths = []
    try:
        mod = get_loader(mod_name)
        source = Path(mod.path)
        if source.name.endswith(".py"):
            source_rel = Path(*mod_name.split("."))
            if source.name == "__init__.py":
                source_rel = source_rel.joinpath("__init__.py")
            destination = Path(out_dir, source_rel.with_suffix(".pyi"))
            paths.append((source, destination))
    except Exception as e:
        _logger.debug(e)
        _logger.warning("cannot handle module, skipping: %s", mod_name)
    return paths


def get_pkg_paths(pkg_name, out_dir):
    """Recursively get all source and stub paths for a package."""
    paths = []
    try:
        pkg = import_module(pkg_name)
        if not hasattr(pkg, "__path__"):
            return get_mod_paths(pkg_name, out_dir)
        for mod_info in walk_packages(pkg.__path__, pkg.__name__ + "."):
            mod_paths = get_mod_paths(mod_info.name, out_dir)
            paths.extend(mod_paths)
    except Exception as e:
        _logger.debug(e)
        _logger.warning("cannot handle package, skipping: %s", pkg_name)
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


def main(argv=None):
    """Start the command line interface."""
    parser = ArgumentParser(prog="pygenstub")
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

    argv = argv if argv is not None else sys.argv
    arguments = parser.parse_args(argv[1:])

    # set debug mode
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)
        _logger.debug("running in debug mode")

    out_dir = arguments.out_dir if arguments.out_dir is not None else ""
    if (out_dir == "") and (len(arguments.modules) > 0):
        print("Output directory must be given when generating stubs for modules.")
        sys.exit(1)

    modules = []
    for path in arguments.files:
        paths = Path(path).glob("**/*.py") if Path(path).is_dir() else [Path(path)]
        for source in paths:
            if str(source).startswith(os.path.pardir):
                source = source.absolute().resolve()
            if (out_dir != "") and source.is_absolute():
                source = source.relative_to(source.root)
            destination = Path(out_dir, source.with_suffix(".pyi"))
            modules.append((source, destination))

    for mod_name in arguments.modules:
        modules.extend(get_pkg_paths(mod_name, out_dir))

    for source, destination in modules:
        _logger.info("generating stub for %s to path %s", source, destination)
        with source.open() as f:
            code = f.read()
        try:
            stub = get_stub(code, generic=arguments.generic)
        except Exception as e:
            print(source, "-", e, file=sys.stderr)
            continue

        if stub != "":
            if not destination.parent.exists():
                destination.parent.mkdir(parents=True)
            with destination.open("w") as f:
                f.write("# " + EDIT_WARNING + "\n\n" + stub)


if __name__ == "__main__":
    main()
