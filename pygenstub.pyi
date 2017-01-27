# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import List, Mapping, Optional, Sequence, Set, Tuple, Union

from collections import OrderedDict

import ast
import docutils.nodes


SIGNATURE_COMMENT = ...  # type: '

def get_fields(
        node: docutils.nodes.document,
        fields_tag: Optional[str] = ...
) -> Mapping[str, str]: ...

def get_signature(
        node: Union[ast.FunctionDef, ast.ClassDef]
) -> Optional[str]: ...

def split_parameter_types(parameters_def: str) -> List[str]: ...

def parse_signature(signature: str) -> Tuple[List[str], str]: ...

class StubNode(object):
    parent = ...    # type: Optional[StubNode]
    children = ...  # type: List[StubNode]

    def __init__(self, parent: Optional['StubNode'] = ...) -> None: ...

    def get_code(self, max_var: Optional[int] = ...) -> str: ...

class ClassNode(StubNode): ...

class FunctionNode(StubNode): ...

class VariableNode(StubNode): ...

class SignatureCollector(ast.NodeVisitor):
    tree = ...            # type: ast.AST
    stub_tree = ...       # type: StubNode
    imported_names = ...  # type: OrderedDict
    defined_types = ...   # type: Set[str]
    required_types = ...  # type: Set[str]
    units = ...           # type: List[StubNode]
    code_lines = ...      # type: Sequence[str]

    def __init__(self, code: str) -> None: ...

    def traverse(self) -> None: ...

def get_stub(code: str) -> str: ...

def main() -> None: ...
