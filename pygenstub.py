# Copyright (c) 2016-2017 H. Turgut Uyar <uyar@tekir.org>
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

from __future__ import print_function, unicode_literals

from argparse import ArgumentParser
from bisect import bisect
from codecs import open
from collections import OrderedDict
from docutils.core import publish_doctree
from io import StringIO

import ast
import logging
import re
import sys

try:
    from textwrap import indent
except ImportError:     # PY2
    def indent(text, lead):
        if lead == '':
            return text
        return '\n'.join([lead + line for line in text.splitlines()]) + '\n'


BUILTIN_TYPES = {
    'int', 'float', 'bool', 'str', 'bytes', 'unicode',
    'tuple', 'list', 'set', 'dict', 'None', 'object'
}

SIGNATURE_FIELD = 'sig'
SIGNATURE_COMMENT = ' # sig: '

LINE_LENGTH_LIMIT = 79
INDENT = 4 * ' '
MULTILINE_INDENT = 2 * INDENT

EDIT_WARNING = 'THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.'

_RE_NAMES = re.compile(r'\w+(?:\.\w+)*')


_logger = logging.getLogger(__name__)


def get_fields(node, fields_tag='field_list'):
    """Get field names and values of a node.

    :sig: (docutils.nodes.document, Optional[str]) -> Mapping[str, str]
    :param node: Node to get the fields from.
    :param fields_tag: Tag of child node that contains the fields.
    :return: Field names and their values.
    """
    fields_nodes = [c for c in node.children if c.tagname == fields_tag]
    if len(fields_nodes) == 0:
        return {}
    assert len(fields_nodes) == 1, 'multiple nodes with tag ' + fields_tag
    fields_node = fields_nodes[0]
    fields = [{f.tagname: f.rawsource.strip() for f in n.children}
              for n in fields_node.children if n.tagname == 'field']
    return {f['field_name']: f['field_body'] for f in fields}


def get_signature(node):
    """Get the signature from the docstring of a node.

    :sig: (Union[ast.FunctionDef, ast.ClassDef]) -> Optional[str]
    :param node: Node to get the signature from.
    :return: Value of signature field in node docstring.
    """
    docstring = ast.get_docstring(node)
    if docstring is None:
        return None
    doc = publish_doctree(docstring, settings_overrides={'report_level': 5})
    fields = get_fields(doc)
    return fields.get(SIGNATURE_FIELD)


def split_parameter_types(parameters_def):
    """Split a full parameter types declaration into individual types.

    :sig: (str) -> List[str]
    :param parameters_def: Parameter types declaration in the signature.
    :return: Types of parameters.
    """
    if parameters_def == '':
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for i, char in enumerate(parameters_def):
        if (char == ',') and (bracket_depth == 0):
            commas.append(i)
        elif char == '[':
            bracket_depth += 1
        elif char == ']':
            bracket_depth -= 1

    types = []
    last_i = 0
    for i in commas:
        types.append(parameters_def[last_i:i].strip())
        last_i = i + 1
    else:
        types.append(parameters_def[last_i:].strip())
    return types


def parse_signature(signature):
    """Parse a signature to get its input and output parameter types.

    :sig: (str) -> Tuple[List[str], str]
    :param signature: Signature to parse.
    :return: Input parameter types and return type.
    """
    lhs, return_type = [s.strip() for s in signature.split(' -> ')]
    parameters_def = lhs[1:-1].strip()  # remove the () around parameter list
    parameter_types = split_parameter_types(parameters_def)
    _logger.debug('parameter types: %s', parameter_types)
    _logger.debug('return type: %s', return_type)
    return parameter_types, return_type


class StubNode(object):
    """A node in a stub tree.

    :sig: (Optional['StubNode']) -> None
    :param parent: Parent node of the node.
    """

    def __init__(self, parent=None):
        self.parent = parent        # sig: Optional[StubNode]
        self.children = []          # sig: List[StubNode]
        if parent is not None:
            parent.children.append(self)

    def get_code(self, max_var=None):
        """Get the prototype code for this node.

        :sig: (Optional[int]) -> str
        """
        var_nodes = [c for c in self.children if isinstance(c, VariableNode)]
        max_len = max([len(v.name) for v in var_nodes])
        var_stubs = ''.join([c.get_code(max_var=max_len) for c in var_nodes])
        code_stubs = '\n'.join([c.get_code() for c in self.children
                                if not isinstance(c, VariableNode)])
        return var_stubs + '\n' + code_stubs


class ClassNode(StubNode):
    """A node representing a class in a stub tree."""

    def __init__(self, parent, name, bases, signature):
        super(ClassNode, self).__init__(parent)
        self.name = name            # sig: str
        self.bases = bases          # sig: Sequence[str]
        self.signature = signature  # sig: str

    def get_code(self):
        if len(self.children) == 0:
            body = ' ...\n'
        else:
            sub_code = super(ClassNode, self).get_code()
            body = '\n' + indent(sub_code, INDENT)
        return 'class %(name)s%(bases)s:%(body)s' % {
            'name': self.name,
            'bases': '(' + ', '.join(self.bases) + ')' if len(self.bases) > 0 else '',
            'body': body
        }


class FunctionNode(StubNode):
    """A node representing a function in a stub tree."""

    def __init__(self, parent, name, signature, ast_node):
        super(FunctionNode, self).__init__(parent)
        self.name = name            # sig: str
        self.signature = signature  # sig: str
        self.ast_node = ast_node    # sig: ast.AST

    def get_code(self):
        parameter_types, return_type = parse_signature(self.signature)
        parameters = [arg.arg if hasattr(arg, 'arg') else arg.id
                      for arg in self.ast_node.args.args]
        if (len(parameters) > 0) and (parameters[0] == 'self'):
            parameter_types.insert(0, '')
        assert len(parameter_types) == len(parameters)

        parameter_locations = [(a.lineno, a.col_offset)
                               for a in self.ast_node.args.args]
        parameter_defaults = {bisect(parameter_locations, (d.lineno, d.col_offset)) - 1
                              for d in self.ast_node.args.defaults}

        parameter_stubs = [
            n + (': ' + t if t != '' else '') + (' = ...' if i in parameter_defaults else '')
            for i, (n, t) in enumerate(zip(parameters, parameter_types))]
        prototype = 'def %(name)s(%(params)s) -> %(rtype)s: ...\n' % {
            'name': self.ast_node.name,
            'params': ', '.join(parameter_stubs),
            'rtype': return_type
        }
        if len(prototype) > LINE_LENGTH_LIMIT:
            prototype = 'def %(name)s(\n%(indent)s%(params)s\n) -> %(rtype)s: ...\n' % {
                'name': self.ast_node.name,
                'indent': MULTILINE_INDENT,
                'params': (',\n' + MULTILINE_INDENT).join(parameter_stubs),
                'rtype': return_type
            }
        return prototype


class VariableNode(StubNode):
    def __init__(self, parent, name, type_):
        super(VariableNode, self).__init__(parent)
        self.name = name    # sig: str
        self.type_ = type_  # sig: str

    def get_code(self, max_var=None):
        if max_var is None:
            max_var = len(self.name)
        return '%(name)s = ... %(space)s # type: %(type)s\n' % {
            'name': self.name,
            'space': (max_var - len(self.name)) * ' ',
            'type': self.type_
        }


class SignatureCollector(ast.NodeVisitor):
    """A collector that scans a source code and gathers signature data.

    :sig: (str) -> None
    :param code: Source code to scan.
    """

    def __init__(self, code):
        self.tree = ast.parse(code)             # sig: ast.AST
        self.stub_tree = StubNode()             # sig: StubNode

        self.imported_names = OrderedDict()     # sig: OrderedDict
        self.defined_types = set()              # sig: Set[str]
        self.required_types = set()             # sig: Set[str]

        self.units = [self.stub_tree]           # sig: List[StubNode]
        self.code = code.splitlines()           # sig: Sequence[str]

    def traverse(self):
        """Recursively visit all nodes of the tree and gather signature data.

        :sig: () -> None
        """
        self.visit(self.tree)

    def visit_ImportFrom(self, node):
        for name in node.names:
            self.imported_names[name.name] = node.module

    def visit_ClassDef(self, node):
        self.defined_types.add(node.name)
        signature = get_signature(node)
        if signature is not None:
            requires = set( _RE_NAMES.findall(signature)) - BUILTIN_TYPES
            self.required_types |= requires

        parent = self.units[-1]
        bases = [n.value.id + '.' + n.attr if isinstance(n, ast.Attribute) else n.id
                 for n in node.bases]
        self.required_types |= set(bases) - BUILTIN_TYPES
        stub_node = ClassNode(parent, node.name, bases=bases, signature=signature)

        self.units.append(stub_node)
        self.generic_visit(node)
        del self.units[-1]

    def visit_FunctionDef(self, node):
        signature = get_signature(node)

        if signature is None:
            parent = self.units[-1]
            if isinstance(parent, ClassNode) and (node.name == '__init__'):
                signature = parent.signature

        if signature is not None:
            requires = set(_RE_NAMES.findall(signature)) - BUILTIN_TYPES
            self.required_types |= requires

            parent = self.units[-1]
            stub_node = FunctionNode(parent, node.name, signature, node)

            self.units.append(stub_node)
            self.generic_visit(node)
            del self.units[-1]

    def visit_Assign(self, node):
        parent = self.units[-1]
        code_line = self.code[node.lineno - 1]
        if SIGNATURE_COMMENT in code_line:
            _, type_ = code_line.split(SIGNATURE_COMMENT)
            requires = set(_RE_NAMES.findall(type_)) - BUILTIN_TYPES
            self.required_types |= requires
            for var in node.targets:
                if isinstance(var, ast.Name):
                    stub_node = VariableNode(parent, var.id, type_.strip())
                if isinstance(var, ast.Attribute) and (var.value.id == 'self'):
                    stub_node = VariableNode(parent.parent, var.attr, type_.strip())

    def get_stub(self):
        needed_types = self.required_types

        needed_types -= self.defined_types
        _logger.debug('defined types: %s', self.defined_types)

        imported_types = set(self.imported_names) & needed_types
        needed_types -= imported_types
        _logger.debug('imported names: %s', self.imported_names)
        _logger.debug('used imported types: %s', imported_types)

        dotted_types = {n for n in needed_types if '.' in n}
        needed_types -= dotted_types
        _logger.debug('dotted types: %s', dotted_types)

        try:
            typing_module = __import__('typing')
            typing_types = {n for n in needed_types if hasattr(typing_module, n)}
            _logger.debug('types from typing module: %s', typing_types)
        except ImportError:
            _logger.debug('typing module not installed')
            typing_types = set()
        needed_types -= typing_types

        if len(needed_types) > 0:
            print('Unknown types: ' + ', '.join(needed_types), file=sys.stderr)
            sys.exit(1)

        out = StringIO()
        started = False

        if len(typing_types) > 0:
            out.write(
                'from typing import ' + ', '.join(sorted(typing_types)) + '\n')
            started = True

        if len(imported_types) > 0:
            if started:
                out.write('\n')
            # preserve the import order in the source file
            for name in self.imported_names:
                if name in imported_types:
                    out.write(
                        'from %(module)s import %(name)s\n' % {
                            'module': self.imported_names[name],
                            'name': name
                        }
                    )
            started = True

        if len(dotted_types) > 0:
            if started:
                out.write('\n')
            imported_modules = {'.'.join(n.split('.')[:-1]) for n in
                                dotted_types}
            for module in sorted(imported_modules):
                out.write('import ' + module + '\n')
            started = True

        if started:
            out.write('\n\n')
        out.write(self.stub_tree.get_code())
        return out.getvalue()


def get_stub(code):
    """Get the stub declarations for a source code.

    :sig: (str) -> str
    :param code: Source code to generate the stub for.
    :return: Stub code for the source.
    """
    collector = SignatureCollector(code)
    collector.traverse()
    return collector.get_stub()


def main():
    """Entry point of the command-line utility.

    :sig: () -> None
    """
    parser = ArgumentParser()
    parser.add_argument('source', help='source file')
    parser.add_argument('--debug', action='store_true', help='enable debug messages')
    arguments = parser.parse_args()

    log_level = logging.DEBUG if arguments.debug else logging.INFO
    logging.basicConfig(level=log_level)

    with open(arguments.source, mode='r', encoding='utf-8') as f_in:
        code = f_in.read()

    stub = get_stub(code)

    destination = arguments.source + 'i'
    if stub != '':
        with open(destination, mode='w', encoding='utf-8') as f_out:
            f_out.write('# ' + EDIT_WARNING + '\n\n')
            f_out.write(stub)


if __name__ == '__main__':
    main()
