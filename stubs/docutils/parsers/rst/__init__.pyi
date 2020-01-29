# Stubs for docutils.parsers.rst (Python 3.6)
#
# NOTE: This dynamically typed stub was automatically generated by stubgen.

import docutils.parsers
import docutils.statemachine
from docutils import nodes
from docutils.nodes import Node
from docutils.parsers.rst.states import Inliner, RSTState, RSTStateMachine
from docutils.statemachine import StringList
from docutils.transforms import Transform
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Type

__docformat__: str

class Parser(docutils.parsers.Parser):
    supported: Tuple[str, ...] = ...
    settings_spec: Tuple[str, str, Tuple[str, List[str], Dict[str, Any]]] = ...
    config_section: str = ...
    config_section_dependencies: Sequence[str] = ...
    initial_state: str = ...
    state_classes: Sequence[Type[RSTState]] = ...
    inliner: Inliner = ...
    def __init__(self, rfc2822: bool = ..., inliner: Optional[Inliner] = ...) -> None: ...
    def get_transforms(self) -> List[Type[Transform]]: ...
    statemachine: RSTStateMachine = ...
    def parse(self, inputstring: str, document: nodes.document) -> None: ...

class DirectiveError(Exception):
    level: int = ...
    msg: str = ...
    def __init__(self, level: int, message: str) -> None: ...

class Directive:
    required_arguments: int = ...
    optional_arguments: int = ...
    final_argument_whitespace: bool = ...
    option_spec: Dict[str, Callable[[str], Any]] = ...
    has_content: bool = ...
    name: str = ...
    arguments: List[str] = ...
    options: Dict[str, Any] = ...
    content: StringList = ...
    lineno: int = ...
    content_offset: int = ...
    block_text: str = ...
    state: RSTState = ...
    state_machine: RSTStateMachine = ...
    def __init__(self, name: str, arguments: List[str], options: Dict[str, Any], content: StringList, lineno: int, content_offset: int, block_text: str, state: RSTState, state_machine: RSTStateMachine) -> None: ...
    def run(self) -> List[nodes.Node]: ...
    def directive_error(self, level: int, message: str) -> DirectiveError: ...
    def debug(self, message: str) -> DirectiveError: ...
    def info(self, message: str) -> DirectiveError: ...
    def warning(self, message: str) -> DirectiveError: ...
    def error(self, message: str) -> DirectiveError: ...
    def severe(self, message: str) -> DirectiveError: ...
    def assert_has_content(self) -> None: ...
    def add_name(self, node: Node) -> None: ...

def convert_directive_function(directive_fn: Callable) -> Directive: ...
