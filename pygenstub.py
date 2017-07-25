# Copyright (c) 2016-2017 H. Turgut Uyar <uyar@tekir.org>
#
# This file is part of pygenstub.
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

"""pygenstub is a utility for generating stub files from Python source files.

It takes a source file as input and creates a stub file with the same base name
and the ``.pyi`` extension.

For documentation, please refer to: https://pygenstub.readthedocs.io/
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import ast
import inspect
import logging
import re
import sys
from argparse import ArgumentParser
from bisect import bisect
from collections import OrderedDict
from io import StringIO

from docutils.core import publish_doctree


PY3 = sys.version_info >= (3, 0)

if not PY3:
    import __builtin__ as builtins
    from codecs import open

    def indent(text, lead):
        """Add some leading text to the beginning of every line in a text."""
        if lead == '':
            return text
        return '\n'.join([lead + line if line else line
                          for line in text.splitlines()]) + '\n'
else:
    import builtins
    from textwrap import indent


BUILTIN_TYPES = {k for k, t in builtins.__dict__.items() if isinstance(t, type)}
BUILTIN_TYPES.add('None')

SIG_FIELD = 'sig'       # sig: str
SIG_COMMENT = '# sig:'  # sig: str

DECORATORS = {'property', 'staticmethod', 'classmethod'}    # sig: Set[str]

LINE_LENGTH_LIMIT = 79
INDENT = 4 * ' '
MULTILINE_INDENT = 2 * INDENT

EDIT_WARNING = 'THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.'

_RE_QUALIFIED_TYPES = re.compile(r'\w+(?:\.\w+)*')
_RE_COMMENT_IN_STRING = re.compile(r'''['"]\s*%(text)s\s*.*['"]''' % {'text': SIG_COMMENT})


_logger = logging.getLogger(__name__)


def get_fields(node, fields_tag='field_list'):
    """Get the field names and their values from a node.

    :sig: (docutils.nodes.document, Optional[str]) -> Mapping[str, str]
    :param node: Node to get the fields from.
    :param fields_tag: Tag of child node that contains the fields.
    :return: Mapping of field names to values.
    """
    fields_nodes = [c for c in node.children if c.tagname == fields_tag]
    if len(fields_nodes) == 0:
        return {}
    assert len(fields_nodes) == 1, 'multiple nodes with tag ' + fields_tag
    fields_node = fields_nodes[0]
    fields = [{f.tagname: f.rawsource.strip() for f in n.children}
              for n in fields_node.children if n.tagname == 'field']
    return {f['field_name']: f['field_body'] for f in fields}


def extract_signature(docstring):
    """Extract the signature from a docstring.

    :sig: (str) -> Optional[str]
    :param docstring: Docstring to extract the signature from.
    :return: Extracted signature, or ``None`` if there's no signature.
    """
    root = publish_doctree(docstring, settings_overrides={'report_level': 5})
    fields = get_fields(root)
    return fields.get(SIG_FIELD)


def get_signature(node):
    """Get the signature of a function or a class.

    :sig: (Union[ast.FunctionDef, ast.ClassDef]) -> Optional[str]
    :param node: Node to get the signature from.
    :return: Value of signature field in node docstring, or ``None`` if there's no signature.
    """
    docstring = ast.get_docstring(node)
    if docstring is None:
        return None
    return extract_signature(docstring)


def split_parameter_types(csv):
    """Split a parameter types declaration into individual types.

    The input is the left hand side of a signature (the part before the arrow),
    excluding the parentheses.

    :sig: (str) -> List[str]
    :param csv: Comma separated list of parameter types.
    :return: List of parameter types.
    """
    if csv == '':
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for i, char in enumerate(csv):
        if (char == ',') and (bracket_depth == 0):
            commas.append(i)
        elif char == '[':
            bracket_depth += 1
        elif char == ']':
            bracket_depth -= 1

    types = []
    last_i = 0
    for i in commas:
        types.append(csv[last_i:i].strip())
        last_i = i + 1
    else:
        types.append(csv[last_i:].strip())
    return types


def parse_signature(signature):
    """Parse a signature into its input and return parameter types.

    This will also collect the types that are required by any of the input
    and return types.

    :sig: (str) -> Tuple[List[str], str, Set[str]]
    :param signature: Signature to parse.
    :return: Input parameter types, return type, and all required types.
    """
    if ' -> ' not in signature:
        # signature comment: no parameters, treat variable type as return type
        param_types, return_type = None, signature.strip()
    else:
        lhs, return_type = [s.strip() for s in signature.split(' -> ')]
        csv = lhs[1:-1].strip()     # remove the parentheses around the parameter type list
        param_types = split_parameter_types(csv)
    requires = set(_RE_QUALIFIED_TYPES.findall(signature))
    return param_types, return_type, requires


class StubNode:
    """A node in a stub tree."""

    def __init__(self):
        """Initialize this stub node.

        :sig: () -> None
        """
        self.variables = []     # sig: List[VariableNode]
        self.children = []      # sig: List[Union[FunctionNode, ClassNode]]
        self.parent = None      # sig: Optional[StubNode]

    def add_variable(self, node):
        """Add a variable node to this node.

        :sig: (VariableNode) -> None
        :param node: Variable node to add.
        """
        self.variables.append(node)
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

        :sig: () -> str
        :return: Stub code for this node.
        """
        max_len = max([len(v.name) for v in self.variables]) if len(self.variables) > 0 else 0
        sub_vars = ''.join([c.get_code(align=max_len) for c in self.variables])
        sub_codes = '\n'.join([c.get_code() for c in self.children])
        return '%(vars)s%(blank)s%(codes)s' % {
            'vars': sub_vars,
            'blank': '\n' if (sub_vars != '') and (sub_codes != '') else '',
            'codes': sub_codes
        }


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
        self.name = name    # sig: str
        self.type_ = type_  # sig: str

    def get_code(self, align=0):
        """Get the type annotation for this variable.

        To align the generated type comments, the caller can send
        an alignment parameter to leave extra space before the comment.

        :sig: (Optional[int]) -> str
        :param align: Number of extra spaces before the start of the comment.
        :return: Type annotation for this variable.
        """
        spaces = max(align - len(self.name), 0)
        return '%(name)s = ... %(space)s # type: %(type)s\n' % {
            'name': self.name,
            'space': spaces * ' ',
            'type': self.type_
        }


class FunctionNode(StubNode):
    """A node representing a function in a stub tree."""

    def __init__(self, name, parameters, rtype, decorators=None):
        """Initialize this function node.

        The parameters have to given as a list of triples where each item specifies
        the name of the parameter, its type, and whether it has a default value or not.

        :sig: (str, List[Tuple[str, str, bool]], str, Optional[List[str]]) -> None
        :param name: Name of function.
        :param parameters: List of parameter triples (name, type, has_default).
        :param rtype: Type of return value.
        :param decorators: Decorators of function.
        """
        if not PY3:
            StubNode.__init__(self)
        else:
            super().__init__()
        self.name = name                # sig: str
        self.parameters = parameters    # sig: List[Tuple[str, str, bool]]
        self.rtype = rtype              # sig: str
        self.decorators = decorators if decorators is not None else []  # sig: List[str]]

    def get_code(self):
        """Get the stub code for this function.

        :sig: () -> str
        :return: Stub code for this function.
        """
        decorators = ['@' + d + '\n' for d in self.decorators if d in DECORATORS]
        parameter_decls = [
            '%(name)s%(type)s%(default)s' % {
                'name': name,
                'type': ': ' + type_ if type_ != '' else '',
                'default': ' = ...' if has_default else ''
            }
            for name, type_, has_default in self.parameters
        ]
        prototype = '%(decs)sdef %(name)s(%(params)s) -> %(rtype)s: ...\n' % {
            'decs': ''.join(decorators),
            'name': self.name,
            'params': ', '.join(parameter_decls),
            'rtype': self.rtype
        }
        if len(prototype) > LINE_LENGTH_LIMIT:
            prototype = '%(decs)sdef %(name)s(\n%(indent)s%(params)s\n) -> %(rtype)s: ...\n' % {
                'decs': ''.join(decorators),
                'name': self.name,
                'indent': MULTILINE_INDENT,
                'params': (',\n' + MULTILINE_INDENT).join(parameter_decls),
                'rtype': self.rtype
            }
        return prototype


class ClassNode(StubNode):
    """A node representing a class in a stub tree."""

    def __init__(self, name, bases, signature=None):
        """Initialize this class node.

        :sig: (str, List[str], Optional[str]) -> None
        :param name: Name of class.
        :param bases: Base classes of class.
        :param signature: Signature of class, to be used in __init__ method.
        """
        if not PY3:
            StubNode.__init__(self)
        else:
            super().__init__()
        self.name = name            # sig: str
        self.bases = bases          # sig: List[str]
        self.signature = signature  # sig: Optional[str]

    def get_code(self):
        """Get the stub code for this class.

        :sig: () -> str
        :return: Stub code for this class.
        """
        super_code = super().get_code() if PY3 else StubNode.get_code(self)
        base_code = indent(super_code, INDENT)
        body = ' ...\n' if len(self.children) == 0 else '\n' + base_code
        bases = ', '.join(self.bases)
        return 'class %(name)s%(bases)s:%(body)s' % {
            'name': self.name,
            'bases': '(' + bases + ')' if bases != '' else '',
            'body': body
        }


class StubGenerator(ast.NodeVisitor):
    """A transformer that generates stub declarations from a source code."""

    def __init__(self, source):
        """Initialize this stub generator.

        :sig: (str) -> None
        :param code: Source code to generate the stub for.
        """
        self.root = StubNode()                  # sig: StubNode

        self.imported_names = OrderedDict()     # sig: Mapping[str, str]
        self.defined_types = set()              # sig: Set[str]
        self.required_types = set()             # sig: Set[str]

        self._parents = [self.root]             # type: list
        self._code_lines = source.splitlines()    # type: list

        ast_tree = ast.parse(source)
        self.visit(ast_tree)

    def visit_ImportFrom(self, node):
        """Process a "from x import y" node.

        :sig: (ast.ImportFrom) -> None
        :param node: Node to process.
        """
        line = self._code_lines[node.lineno - 1]
        module_name = line.split('from')[1].split('import')[0].strip()
        for name in node.names:
            self.imported_names[name.name] = module_name

    def visit_Assign(self, node):
        """Process an assignment node.

        :sig: (ast.Assign) -> None
        :param node: Node to process.
        """
        line = self._code_lines[node.lineno - 1]
        if SIG_COMMENT in line:
            line = _RE_COMMENT_IN_STRING.sub('', line)
        if SIG_COMMENT in line:
            _, signature = line.split(SIG_COMMENT)
            _, return_type, requires = parse_signature(signature)
            self.required_types |= requires

            parent = self._parents[-1]
            for var in node.targets:
                if isinstance(var, ast.Name):
                    stub_node = VariableNode(var.id, return_type)
                    parent.add_variable(stub_node)
                if isinstance(var, ast.Attribute) and (var.value.id == 'self'):
                    stub_node = VariableNode(var.attr, return_type)
                    parent.parent.add_variable(stub_node)

    def visit_FunctionDef(self, node):
        """Process a function node.

        :sig: (ast.FunctionDef) -> None
        :param node: Node to process.
        """
        signature = get_signature(node)

        if signature is None:
            parent = self._parents[-1]
            if isinstance(parent, ClassNode) and (node.name == '__init__'):
                signature = parent.signature

        if signature is not None:
            _logger.debug('parsing signature for %s', node.name)
            param_types, rtype, requires = parse_signature(signature)
            _logger.debug('parameter types: %s', param_types)
            _logger.debug('return type: %s', rtype)
            _logger.debug('required types: %s', requires)
            self.required_types |= requires

            param_names = [arg.arg if PY3 else arg.id for arg in node.args.args]

            # TODO: only in classes
            if (len(param_names) > 0) and (param_names[0] == 'self'):
                param_types.insert(0, '')

            if node.args.vararg is not None:
                param_names.append('*' + (node.args.vararg.arg if PY3 else node.args.vararg))
                param_types.append('')

            if node.args.kwarg is not None:
                param_names.append('**' + (node.args.kwarg.arg if PY3 else node.args.kwarg))
                param_types.append('')

            assert len(param_types) == len(param_names), node.name

            param_locs = [(a.lineno, a.col_offset) for a in node.args.args]
            param_defaults = {bisect(param_locs, (d.lineno, d.col_offset)) - 1
                              for d in node.args.defaults}

            params = [(name, type_, i in param_defaults)
                      for i, (name, type_) in enumerate(zip(param_names, param_types))]

            decorators = [d.id for d in node.decorator_list]

            stub_node = FunctionNode(node.name, parameters=params, rtype=rtype,
                                     decorators=decorators)
            self._parents[-1].add_child(stub_node)

            self._parents.append(stub_node)
            self.generic_visit(node)
            del self._parents[-1]

    def visit_ClassDef(self, node):
        """Process a class node.

        :sig: (ast.ClassDef) -> None
        :param node: Node to process.
        """
        self.defined_types.add(node.name)

        bases = [n.value.id + '.' + n.attr if isinstance(n, ast.Attribute) else n.id
                 for n in node.bases]
        self.required_types |= set(bases)

        signature = get_signature(node)
        stub_node = ClassNode(node.name, bases=bases, signature=signature)
        self._parents[-1].add_child(stub_node)

        self._parents.append(stub_node)
        self.generic_visit(node)
        del self._parents[-1]

    def generate_stub(self):
        """Generate the stub code for this source.

        :sig: () -> str
        :return: Generated stub code.
        """
        needed_types = self.required_types - BUILTIN_TYPES

        needed_types -= self.defined_types
        _logger.debug('defined types: %s', self.defined_types)

        module_vars = {v.name for v in self.root.variables}
        _logger.debug('module variables: %s', module_vars)

        dotted_types = {n for n in needed_types if '.' in n}
        dotted_namespaces = {'.'.join(n.split('.')[:-1]) for n in dotted_types}

        needed_namespaces = dotted_namespaces - module_vars
        needed_types -= dotted_types
        _logger.debug('needed namespaces: %s', needed_namespaces)

        imported_names = set(self.imported_names)
        imported_types = imported_names & (needed_types | needed_namespaces)
        needed_types -= imported_types
        needed_namespaces -= imported_names
        _logger.debug('used imported types: %s', imported_types)

        try:
            typing_mod = __import__('typing')
            typing_types = {n for n in needed_types if hasattr(typing_mod, n)}
            needed_types -= typing_types
            _logger.debug('types from typing module: %s', typing_types)
        except ImportError:
            typing_types = set()
            _logger.warn('typing module not installed')

        if len(needed_types) > 0:
            raise RuntimeError('Unknown types: ' + ', '.join(needed_types))

        out = StringIO()
        started = False

        if len(typing_types) > 0:
            line = 'from typing import ' + ', '.join(sorted(typing_types))
            out.write(line + '\n')
            started = True

        if len(imported_types) > 0:
            if started:
                out.write('\n')
            # preserve the import order in the source file
            for name in self.imported_names:
                if name in imported_types:
                    line = 'from %(module)s import %(name)s' % {
                        'module': self.imported_names[name],
                        'name': name
                    }
                    out.write(line + '\n')
            started = True

        if len(needed_namespaces) > 0:
            if started:
                out.write('\n')
            for module in sorted(needed_namespaces):
                out.write('import ' + module + '\n')
            started = True

        if started:
            out.write('\n\n')
        out.write(self.root.get_code())
        return out.getvalue()


def get_stub(source):
    """Get the stub code for a source code.

    :sig: (str) -> str
    :param source: Source code to generate the stub for.
    :return: Generated stub code.
    """
    generator = StubGenerator(source)
    return generator.generate_stub()


def process_docstring(app, what, name, obj, options, lines):
    """Modify the docstring before generating documentation.

    This will insert type declarations for parameters and return type
    into the docstring, and remove the signature field so that it will
    be excluded from the generated document.
    """
    signature = extract_signature('\n'.join(lines))
    if signature is None:
        return

    if what in ('class', 'exception'):
        obj = getattr(obj, '__init__')

    param_types, rtype, _ = parse_signature(signature)
    param_names = [p for p in inspect.signature(obj).parameters]

    if (what in ('class', 'exception')) and (param_names[0] == 'self'):
        del param_names[0]

    # if something goes wrong, don't insert parameter types
    if len(param_names) == len(param_types):
        for name, type_ in zip(param_names, param_types):
            find = ':param %(name)s:' % {'name': name}
            for i, line in enumerate(lines):
                if line.startswith(find):
                    lines.insert(i, ':type %(name)s: %(type)s' % {'name': name, 'type': type_})
                    break

    if what not in ('class', 'exception'):
        for i, line in enumerate(lines):
            if line.startswith((':return:', ':returns:')):
                lines.insert(i, ':rtype: ' + rtype)
                break

    # remove the signature field
    sig_marker = ':' + SIG_FIELD + ':'
    sig_start = 0
    while sig_start < len(lines):
        if lines[sig_start].startswith(sig_marker):
            break
        sig_start += 1
    sig_end = sig_start + 1
    while sig_end < len(lines):
        if (not lines[sig_end]) or (lines[sig_end][0] != ' '):
            break
        sig_end += 1
    for i in reversed(range(sig_start, sig_end)):
        del lines[i]


def setup(app):
    """Register the Sphinx extension."""
    app.connect('autodoc-process-docstring', process_docstring)
    return dict(parallel_read_safe=True)


def main(argv=None):
    """Entry point of the command-line utility.

    :sig: (Optional[List[str]]) -> None
    :param argv: Command line arguments.
    """
    argv = argv if argv is not None else sys.argv
    parser = ArgumentParser(prog=argv[0])
    parser.add_argument('source', help='source file')
    parser.add_argument('--debug', action='store_true', help='enable debug messages')
    arguments = parser.parse_args(argv[1:])

    # set debug mode
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)
        _logger.debug('running in debug mode')

    with open(arguments.source, mode='r', encoding='utf-8') as f_in:
        code = f_in.read()

    try:
        stub = get_stub(code)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    if stub != '':
        destination = arguments.source + 'i'
        with open(destination, mode='w', encoding='utf-8') as f_out:
            f_out.write('# ' + EDIT_WARNING + '\n\n')
            f_out.write(stub)


if __name__ == '__main__':
    main()
