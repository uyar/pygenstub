# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import List, Mapping, Optional, Set, Tuple, Union

import ast
import docutils.nodes


SIG_FIELD = ...    # type: str
SIG_COMMENT = ...  # type: str

def get_fields(
        node: docutils.nodes.document,
        fields_tag: Optional[str] = ...
) -> Mapping[str, str]: ...

def get_signature(
        node: Union[ast.FunctionDef, ast.ClassDef]
) -> Optional[str]: ...

def split_parameter_types(decl: str) -> List[str]: ...

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
    name = ...         # type: str
    parameters = ...   # type: List[Tuple[str, str, bool]]
    return_type = ...  # type: str

    def __init__(
            self,
            name: str,
            parameters: List[Tuple[str, str, bool]],
            return_type: str
    ) -> None: ...

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
    imported_names = ...  # type: Mapping[str, str]
    defined_types = ...   # type: Set[str]
    required_types = ...  # type: Set[str]

    def __init__(self, code: str) -> None: ...

    def generate_stub(self) -> str: ...

def get_stub(code: str) -> str: ...

def main() -> None: ...
