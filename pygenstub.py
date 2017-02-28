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

from argparse import ArgumentParser
from bisect import bisect
from collections import OrderedDict
from docutils.core import publish_doctree
from io import StringIO

import ast
import logging
import re
import sys
import textwrap


BUILTIN_TYPES = {
    'int', 'float', 'bool', 'str', 'bytes', 'unicode',
    'tuple', 'list', 'set', 'dict', 'None', 'object'
}

SIGNATURE_FIELD = 'sig'         # sig: str
SIGNATURE_COMMENT = '# sig:'    # sig: str

LINE_LENGTH_LIMIT = 79
INDENT = 4 * ' '
MULTILINE_INDENT = 2 * INDENT

EDIT_WARNING = 'THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.'

_RE_NAMES = re.compile(r'\w+(?:\.\w+)*')
_RE_SIG_IN_STRING = re.compile(r'''['"]\s*%s\s*.*['"]''' % (SIGNATURE_COMMENT,))


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


def split_parameter_types(decl):
    """Split a parameter types declaration into individual types.

    :sig: (str) -> List[str]
    :param decl: Parameter types declaration in the signature.
    :return: Types of parameters.
    """
    if decl == '':
        return []

    # only consider the top level commas, ignore the ones in []
    commas = []
    bracket_depth = 0
    for i, char in enumerate(decl):
        if (char == ',') and (bracket_depth == 0):
            commas.append(i)
        elif char == '[':
            bracket_depth += 1
        elif char == ']':
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
    """Parse a signature into its input and return parameter types.

    :sig: (str) -> Tuple[List[str], str, Set[str]]
    :param signature: Signature to parse.
    :return: Input parameter types, return type, and all required types.
    """
    if ' -> ' not in signature:
        param_types, return_type = None, signature.strip()
    else:
        lhs, return_type = [s.strip() for s in signature.split(' -> ')]
        param_decl = lhs[1:-1].strip()  # remove the () around parameter list
        param_types = split_parameter_types(param_decl)
    requires = set(_RE_NAMES.findall(signature))
    return param_types, return_type, requires


class StubNode:
    """A node in a stub tree.

    :sig: () -> None
    """
    def __init__(self):
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
        """Add a function or class node to this node.

        :sig: (Union[FunctionNode, ClassNode]) -> None
        :param node: Variable node to add.
        """
        self.children.append(node)
        node.parent = self

    def get_code(self):
        """Get the prototype code for this node.

        :sig: () -> str
        """
        max_len = max([len(v.name) for v in self.variables] + [0])
        sub_vars = ''.join([c.get_code(align=max_len) for c in self.variables])
        sub_codes = '\n'.join([c.get_code() for c in self.children])
        return sub_vars + ('\n' if sub_vars != '' else '') + sub_codes


class VariableNode(StubNode):
    """A node representing an assignment in a stub tree.

    :sig: (str, str) -> None
    :param name: Name of variable that is being assigned to.
    :param type_: Type of variable.
    """
    def __init__(self, name, type_):
        super().__init__()
        self.name = name    # sig: str
        self.type_ = type_  # sig: str

    def get_code(self, align=0):
        """Get the prototype code for this variable.

        :sig: (Optional[int]) -> str
        :param align: Position of hash symbol for alignment.
        """
        spaces = max(align - len(self.name), 0)
        return '%(name)s = ... %(space)s # type: %(type)s\n' % {
            'name': self.name,
            'space': spaces * ' ',
            'type': self.type_
        }


class FunctionNode(StubNode):
    """A node representing a function in a stub tree.

    :sig: (str, List[Tuple[str, str, bool]], str) -> None
    :param name: Name of function.
    """
    def __init__(self, name, parameters, return_type):
        super().__init__()
        self.name = name                # sig: str
        self.parameters = parameters    # sig: List[Tuple[str, str, bool]]
        self.return_type = return_type  # sig: str

    def get_code(self):
        parameter_decls = [
            name + (': ' + type_ if type_ != '' else '') + (' = ...' if has_default else '')
            for name, type_, has_default in self.parameters
        ]
        prototype = 'def %(name)s(%(params)s) -> %(rtype)s: ...\n' % {
            'name': self.name,
            'params': ', '.join(parameter_decls),
            'rtype': self.return_type
        }
        if len(prototype) > LINE_LENGTH_LIMIT:
            prototype = 'def %(name)s(\n%(indent)s%(params)s\n) -> %(rtype)s: ...\n' % {
                'name': self.name,
                'indent': MULTILINE_INDENT,
                'params': (',\n' + MULTILINE_INDENT).join(parameter_decls),
                'rtype': self.return_type
            }
        return prototype


class ClassNode(StubNode):
    """A node representing a class in a stub tree.

    :sig: (str, List[str], Optional[str]) -> None
    :param name: Name of class.
    :param bases: Base classes of class.
    :param signature: Signature of class, to be used in __init__ method.
    """
    def __init__(self, name, bases, signature=None):
        super().__init__()
        self.name = name            # sig: str
        self.bases = bases          # sig: List[str]
        self.signature = signature  # sig: Optional[str]

    def get_code(self):
        """Get the prototype code for this class.

        :sig: () -> str
        """
        body = ' ...\n' if len(self.children) == 0 else \
            '\n' + textwrap.indent(super().get_code(), INDENT)
        bases = ', '.join(self.bases)
        return 'class %(name)s%(bases)s:%(body)s' % {
            'name': self.name,
            'bases': '(' + bases + ')' if bases != '' else '',
            'body': body
        }


class StubGenerator(ast.NodeVisitor):
    """A transformer that generates stub declarations from a source code.

    :sig: (str) -> None
    :param code: Source code to generate the stub for.
    """
    def __init__(self, code):
        self.root = StubNode()                  # sig: StubNode

        self.imported_names = OrderedDict()     # sig: Mapping[str, str]
        self.defined_types = set()              # sig: Set[str]
        self.required_types = set()             # sig: Set[str]

        self._parents = [self.root]             # type: list
        self._code_lines = code.splitlines()    # type: list

        ast_tree = ast.parse(code)
        self.visit(ast_tree)

    def visit_ImportFrom(self, node):
        line = self._code_lines[node.lineno - 1]
        module_name = line.split('from')[1].split('import')[0].strip()
        for name in node.names:
            self.imported_names[name.name] = module_name

    def visit_Assign(self, node):
        line = self._code_lines[node.lineno - 1]
        if SIGNATURE_COMMENT in line:
            line = _RE_SIG_IN_STRING.sub('', line)
        if SIGNATURE_COMMENT in line:
            _, signature = line.split(SIGNATURE_COMMENT)
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
        signature = get_signature(node)

        if signature is None:
            parent = self._parents[-1]
            if isinstance(parent, ClassNode) and (node.name == '__init__'):
                signature = parent.signature

        if signature is not None:
            _logger.debug('parsing signature for %s', node.name)
            arg_types, rtype, requires = parse_signature(signature)
            _logger.debug('parameter types: %s', arg_types)
            _logger.debug('return type: %s', rtype)
            _logger.debug('required types: %s', requires)
            self.required_types |= requires

            arg_names = [arg.arg for arg in node.args.args]
            if (len(arg_names) > 0) and (arg_names[0] == 'self'):
                arg_types.insert(0, '')

            if node.args.vararg is not None:
                arg_names.append('*' + node.args.vararg.arg)
                arg_types.append('')

            if node.args.kwarg is not None:
                arg_names.append('**' + node.args.kwarg.arg)
                arg_types.append('')

            assert len(arg_types) == len(arg_names), node.name
            args = zip(arg_names, arg_types)

            arg_locs = [(a.lineno, a.col_offset) for a in node.args.args]
            arg_defaults = {bisect(arg_locs, (d.lineno, d.col_offset)) - 1
                            for d in node.args.defaults}

            params = [(name, type_, i in arg_defaults)
                      for i, (name, type_) in enumerate(args)]
            stub_node = FunctionNode(node.name, parameters=params, return_type=rtype)
            self._parents[-1].add_child(stub_node)

            self._parents.append(stub_node)
            self.generic_visit(node)
            del self._parents[-1]

    def visit_ClassDef(self, node):
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
            print('Unknown types: ' + ', '.join(needed_types), file=sys.stderr)
            sys.exit(1)

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


def get_stub(code):
    """Get the stub declarations for a source code.

    :sig: (str) -> str
    :param code: Source code to generate the stub for.
    :return: Generated stub code.
    """
    generator = StubGenerator(code)
    return generator.generate_stub()


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

    if stub != '':
        destination = arguments.source + 'i'
        with open(destination, mode='w', encoding='utf-8') as f_out:
            f_out.write('# ' + EDIT_WARNING + '\n\n')
            f_out.write(stub)


if __name__ == '__main__':
    main()
