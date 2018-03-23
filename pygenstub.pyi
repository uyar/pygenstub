# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import Dict, List, Mapping, MutableMapping, Optional, Set, Tuple, Union

import ast
import docutils.nodes

Document = docutils.nodes.document

SIG_FIELD = ...    # type: str
SIG_COMMENT = ...  # type: str
SIG_ALIAS = ...    # type: str
DECORATORS = ...   # type: Set[str]

def get_fields(
        node: Document,
        fields_tag: Optional[str] = ...
) -> Mapping[str, str]: ...

def extract_signature(docstring: str) -> Optional[str]: ...

def get_signature(
        node: Union[ast.FunctionDef, ast.ClassDef]
) -> Optional[str]: ...

def split_parameter_types(csv: str) -> List[str]: ...

def parse_signature(signature: str) -> Tuple[List[str], str, Set[str]]: ...

class StubNode:
    variables = ...  # type: List[VariableNode]
    children = ...   # type: List[Union[FunctionNode, ClassNode]]
    parent = ...     # type: Optional[StubNode]

    def __init__(self) -> None: ...

    def add_variable(self, node: VariableNode) -> None: ...

    def add_child(self, node: Union[FunctionNode, ClassNode]) -> None: ...

    def get_code(self) -> str: ...

class VariableNode(StubNode):
    name = ...   # type: str
    type_ = ...  # type: str

    def __init__(self, name: str, type_: str) -> None: ...

    def get_code(self, align: Optional[int] = ...) -> str: ...

class FunctionNode(StubNode):
    name = ...        # type: str
    parameters = ...  # type: List[Tuple[str, str, bool]]
    rtype = ...       # type: str
    decorators = ...  # type: List[str]]

    def __init__(
            self,
            name: str,
            parameters: List[Tuple[str, str, bool]],
            rtype: str,
            decorators: Optional[List[str]] = ...
    ) -> None: ...

    def get_code(self) -> str: ...

class ClassNode(StubNode):
    name = ...       # type: str
    bases = ...      # type: List[str]
    signature = ...  # type: Optional[str]

    def __init__(
            self,
            name: str,
            bases: List[str],
            signature: Optional[str] = ...
    ) -> None: ...

    def get_code(self) -> str: ...

class StubGenerator(ast.NodeVisitor):
    root = ...            # type: StubNode
    imported_names = ...  # type: MutableMapping[str, str]
    defined_types = ...   # type: Set[str]
    required_types = ...  # type: Set[str]
    aliases = ...         # type: Dict[str, str]
    _parents = ...        # type: List[StubNode]
    _code_lines = ...     # type: List[str]

    def __init__(self, source: str) -> None: ...

    def collect_aliases(self) -> None: ...

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None: ...

    def visit_Assign(self, node: ast.Assign) -> None: ...

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None: ...

    def visit_ClassDef(self, node: ast.ClassDef) -> None: ...

    def generate_stub(self) -> str: ...

def get_stub(source: str) -> str: ...

def main(argv: Optional[List[str]] = ...) -> None: ...
