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


BUILTIN_TYPES = {
    'int', 'float', 'bool', 'str', 'bytes', 'unicode',
    'tuple', 'list', 'set', 'dict', 'None'
}

if sys.version_info[0] > 2:
    basestring = (str, bytes)

EDIT_WARNING = 'THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.'


_logger = logging.getLogger(__name__)


def get_fields(node, fields_tag='field_list'):
    """Get field names and values of a node.

    :signature: (docutils.nodes.document, str) -> Mapping[str, str]
    :param node: Node to get the fields from.
    :param fields_tag: Tag of child node that contains the fields.
    :return: Field names and their values.
    """
    fields_nodes = [c for c in node.children if c.tagname == fields_tag]
    if len(fields_nodes) == 0:
        return {}
    assert len(fields_nodes) == 1
    fields_node = fields_nodes[0]
    # [6:] strips the 'field_' prefix
    fields = [{f.tagname[6:]: f.rawsource.strip() for f in n.children}
              for n in fields_node.children if n.tagname == 'field']
    return {f['name']: f['body'] for f in fields}


def get_prototype(node):
    """Get the prototype for a function.

    :signature: (ast.FunctionDef) -> Optional[Tuple[str, Set[str]]]
    :param node: Function node to get the prototype for.
    :return: Prototype and required type names.
    """
    def get_param(i, n, t, defaults):
        s = StringIO()
        s.write('%s: %s' % (n, t))
        if (i + 1) in defaults:
            d = defaults[i + 1]
            if isinstance(d, ast.Str):
                dv = "'%s'" % (getattr(d, d._fields[0]),)
            elif isinstance(d, ast.Tuple):
                dv = '%s' % (tuple(getattr(d, d._fields[0])),)
            else:
                dv = '%s' % (getattr(d, d._fields[0]),)
            s.write(' = %s' % (dv,))
        return s.getvalue()

    docstring = ast.get_docstring(node)
    if docstring is not None:
        doctree = publish_doctree(docstring, settings_overrides={'report_level': 5})
        fields = get_fields(doctree)
        signature = fields.get('signature')
        if signature is not None:
            _logger.debug('parsing signature for %s', node.name)
            lhs, rtype = [s.strip() for s in signature.split(' -> ')]
            pstr = lhs[1:-1].strip()    # remove the () around parameter list

            if pstr == '':
                ptypes = []
            else:
                commas = []
                bracket_depth = 0
                for i, c in enumerate(pstr):
                    if (c == ',') and (bracket_depth == 0):
                        commas.append(i)
                    elif c == '[':
                        bracket_depth += 1
                    elif c == ']':
                        bracket_depth -= 1
                ptypes = []
                last_i = 0
                for i in commas:
                    ptypes.append(pstr[last_i:i].strip())
                    last_i = i + 1
                else:
                    ptypes.append(pstr[last_i:].strip())

            _logger.debug('parameter types: %s', ptypes)
            _logger.debug('return type: %s', rtype)

            params = [arg.arg if hasattr(arg, 'arg') else arg.id
                      for arg in node.args.args]
            assert len(ptypes) == len(params)

            arg_locs = [(a.lineno, a.col_offset) for a in node.args.args]
            arg_defaults = {bisect(arg_locs, (d.lineno, d.col_offset)): d
                            for d in node.args.defaults}

            pstub = ', '.join([get_param(i, n, t, arg_defaults)
                               for i, (n, t) in enumerate(zip(params, ptypes))])
            prototype = 'def %s(%s) -> %s: ...\n' % (node.name, pstub, rtype)
            if len(prototype) > 79:
                pstub = ',\n        '.join(
                    [get_param(i, n, t, arg_defaults)
                     for i, (n, t) in enumerate(zip(params, ptypes))]
                )
                prototype = 'def %s(\n        %s\n) -> %s: ...\n' % (node.name, pstub, rtype)
            requires = {n for n in re.findall(r'\w+(?:\.\w+)*', signature)
                        if n not in BUILTIN_TYPES}
            _logger.debug('requires %s', requires)
            _logger.debug('prototype: %s', prototype)
            return prototype, requires
    return None


def get_stub(code):
    """Get the stub declarations for a source code.

    :signature: (str) -> str
    :param code: Source code to generate the stub for.
    :return: Stub declarations for the source code.
    """
    stub = StringIO()
    tree = ast.parse(code)

    imported_names = OrderedDict([(name.name, node.module)
                                  for node in tree.body
                                  if isinstance(node, ast.ImportFrom)
                                  for name in node.names])
    _logger.debug('imported names: %s', imported_names)

    signatures = OrderedDict(filter(lambda x: x[1] is not None,
                                    [(node.name, get_prototype(node))
                                     for node in tree.body
                                     if isinstance(node, ast.FunctionDef)]))

    if len(signatures) > 0:
        required_names = {n for _, r in signatures.values() for n in r}
        if len(required_names) > 0:
            known_names = [n for n in imported_names if n in required_names]
            unknown_names = required_names - set(imported_names.keys())

            dotted_names = {n for n in unknown_names if '.' in n}
            imported_modules = {'.'.join(n.split('.')[:-1]) for n in dotted_names}

            remaining_names = unknown_names - dotted_names

            try:
                typing_module = __import__('typing')
                typing_names = {n for n in remaining_names if hasattr(typing_module, n)}
                _logger.debug('names from typing module: %s', typing_names)
            except ImportError:
                _logger.debug('typing module not installed')
                typing_names = set()

            missing_names = remaining_names - typing_names
            if len(missing_names) > 0:
                print('Following names could not be found: %s' % (', '.join(missing_names)),
                      file=sys.stderr)
                sys.exit(1)

            started = False

            if len(typing_names) > 0:
                stub.write('from typing import %s\n' % (', '.join(sorted(typing_names)),))
                started = True

            if len(known_names) > 0:
                if started:
                    stub.write('\n')
                for name in known_names:
                    stub.write('from %s import %s\n' % (imported_names[name], name))
                    started = True

            if len(imported_modules) > 0:
                if started:
                    stub.write('\n')
                for module in sorted(imported_modules):
                    stub.write('import %s\n' % (module,))

            stub.write('\n\n')
        stub.write('\n\n'.join([s for s, _ in signatures.values()]))
    return stub.getvalue()


def main():
    """Entry point of the command-line utility.

    :signature: () -> None
    """
    parser = ArgumentParser()
    parser.add_argument('source', help='source file to generate the stub for')
    parser.add_argument('--debug', action='store_true', help='enable debug messages')
    arguments = parser.parse_args()

    log_level = logging.DEBUG if arguments.debug else logging.INFO
    logging.basicConfig(level=log_level)

    with open(arguments.source, mode='r', encoding='utf-8') as f_in:
        code = f_in.read()

    stub = get_stub(code)

    destination = arguments.source + 'i'
    if len(stub) > 0:
        with open(destination, mode='w', encoding='utf-8') as f_out:
            f_out.write('# %s\n\n' % (EDIT_WARNING,))
            f_out.write(stub)


if __name__ == '__main__':
    main()
