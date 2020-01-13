# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import Dict, List, Optional, Sequence, Set, Tuple, Union

import ast
import docutils.nodes

Document = docutils.nodes.document

__version__ = ...  # type: str
SIG_FIELD = ...  # type: str
SIG_COMMENT = ...  # type: str
SIG_ALIAS = ...  # type: str
DECORATORS = ...  # type: Set[str]

def get_fields(node: Document, fields_tag: str = ...) -> Dict[str, str]: ...
def extract_signature(docstring: str) -> Optional[str]: ...
def get_signature(
    node: Union[ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef]
) -> Optional[str]: ...
def split_parameter_types(parameters: str) -> List[str]: ...
def parse_signature(signature: str) -> Tuple[List[str], str, Set[str]]: ...

class StubNode:
    variables = ...  # type: List[VariableNode]
    variable_names = ...  # type: Set[str]
    children = ...  # type: List[Union[FunctionNode, ClassNode]]
    parent = ...  # type: Optional[StubNode]
    def __init__(self) -> None: ...
    def add_variable(self, node: VariableNode) -> None: ...
    def add_child(self, node: Union[FunctionNode, ClassNode]) -> None: ...
    def get_code(self) -> List[str]: ...

class VariableNode(StubNode):
    name = ...  # type: str
    type_ = ...  # type: str
    def __init__(self, name: str, type_: str) -> None: ...
    def get_code(self) -> List[str]: ...

class FunctionNode(StubNode):
    name = ...  # type: str
    parameters = ...  # type: Sequence[Tuple[str, str, bool]]
    rtype = ...  # type: str
    decorators = ...  # type: Sequence[str]
    _async = ...  # type: bool
    def __init__(
        self,
        name: str,
        parameters: Sequence[Tuple[str, str, bool]],
        rtype: str,
        decorators: Optional[Sequence[str]] = ...,
    ) -> None: ...
    def get_code(self) -> List[str]: ...

class ClassNode(StubNode):
    name = ...  # type: str
    bases = ...  # type: Sequence[str]
    signature = ...  # type: Optional[str]
    def __init__(
        self, name: str, bases: Sequence[str], signature: Optional[str] = ...
    ) -> None: ...
    def get_code(self) -> List[str]: ...

def get_aliases(lines: Sequence[str]) -> Dict[str, str]: ...

class StubGenerator(ast.NodeVisitor):
    root = ...  # type: StubNode
    generic = ...  # type: bool
    imported_namespaces = ...  # type: Dict[str, str]
    imported_names = ...  # type: Dict[str, str]
    defined_types = ...  # type: Set[str]
    required_types = ...  # type: Set[str]
    aliases = ...  # type: Dict[str, str]
    _parents = ...  # type: List[StubNode]
    _code_lines = ...  # type: List[str]
    def __init__(self, source: str, generic: bool = ...) -> None: ...
    def collect_aliases(self) -> None: ...
    def get_function_node(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> FunctionNode: ...
    @staticmethod
    def generate_import_from(module_: str, names: Set[str]) -> str: ...
    def generate_stub(self) -> str: ...

def get_stub(source: str, generic: bool = ...) -> str: ...
