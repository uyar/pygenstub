# THIS FILE IS AUTOMATICALLY GENERATED, DO NOT EDIT MANUALLY.

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from argparse import ArgumentParser
from pathlib import Path

import ast

__version__: str

def collect_aliases(lines: Sequence[str]) -> Dict[str, str]: ...
def collect_signatures(lines: Sequence[str]) -> Dict[str, str]: ...
def _split_types(decl: str) -> List[str]: ...
def parse_signature(
    signature: str
) -> Tuple[Optional[List[str]], str, Set[str]]: ...
def print_import_from(
    mod: str, names: Set[str], *, indent: str = ..., **config: Dict[str, Any]
) -> None: ...

class StubNode:
    parent: Optional[StubNode]
    children: List[StubNode]
    def __init__(self) -> None: ...
    def add_child(self, node: StubNode) -> None: ...
    def get_code(self) -> List[str]: ...

class VariableNode(StubNode):
    name: str
    type_: str
    def __init__(self, name: str, type_: str) -> None: ...
    def get_code(self) -> List[str]: ...

class FunctionNode(StubNode):
    name: str
    async_: bool
    parameters: Sequence[Tuple[str, str, bool]]
    rtype: str
    decorators: Sequence[str]
    def __init__(
        self,
        name: str,
        parameters: Sequence[Tuple[str, str, bool]],
        rtype: str,
        *,
        decorators: Optional[Sequence[str]] = ...,
    ) -> None: ...
    def get_code(self) -> List[str]: ...

class ClassNode(StubNode):
    name: str
    bases: Sequence[str]
    signature: Optional[str]
    def __init__(
        self, name: str, *, bases: Sequence[str], signature: Optional[str] = ...
    ) -> None: ...
    def get_code(self) -> List[str]: ...

class StubGenerator(ast.NodeVisitor):
    root: StubNode
    generic: bool
    imported_namespaces: Dict[str, str]
    imported_names: Dict[str, str]
    defined_types: Set[str]
    required_types: Set[str]
    aliases: Dict[str, str]
    _parents: List[StubNode]
    _code_lines: List[str]
    def __init__(self, source: str, *, generic: bool = ...) -> None: ...
    def collect_aliases(self) -> None: ...
    def get_function_node(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> Optional[FunctionNode]: ...
    def analyze_types(self) -> Dict[str, Set[str]]: ...
    def print_stub(self) -> None: ...

def get_stub(source: str, *, generic: bool = ...) -> str: ...
def get_mod_paths(mod_name: str) -> Optional[Tuple[Path, Path]]: ...
def get_pkg_paths(pkg_name: str) -> List[Tuple[Path, Path]]: ...
def _make_parser(prog: str) -> ArgumentParser: ...
def _collect_sources(
    files: List[str], modules: List[str]
) -> List[Tuple[Path, Path]]: ...
def run(argv: Optional[List[str]] = ...) -> None: ...
