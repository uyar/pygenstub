from pygenstub import get_stub


code_template = '''
from x import A, B

def f(%(params)s):
    """Func

    :sig: (%(ptypes)s) -> %(rtype)s
    """
'''


def test_get_stub_no_docstring():
    code = '''def f():\n    pass\n'''
    assert get_stub(code) == ''


def test_get_stub_no_sig():
    code = '''def f():\n    """Func\n    """\n'''
    assert get_stub(code) == ''


def test_get_stub_missing_sig():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'None'} + \
           '''def g():\n    """Func\n    """\n'''
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_params_none_returns_none():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'None'}
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_returns_builtin():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'int'}
    assert get_stub(code) == 'def f() -> int: ...\n'


def test_get_stub_returns_imported():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'A'}
    assert get_stub(code) == 'from x import A\n\n\ndef f() -> A: ...\n'


def test_get_stub_returns_dotted():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'r.s.T'}
    assert get_stub(code) == 'import r.s\n\n\ndef f() -> r.s.T: ...\n'


def test_get_stub_returns_typing():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'List'}
    assert get_stub(code) == 'from typing import List\n\n\ndef f() -> List: ...\n'


def test_get_stub_returns_typing_qualified():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'List[str]'}
    assert get_stub(code) == 'from typing import List\n\n\ndef f() -> List[str]: ...\n'


def test_get_stub_returns_typing_qualified_multiple():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'Dict[str, Any]'}
    assert get_stub(code) == 'from typing import Any, Dict\n\n\ndef f() -> Dict[str, Any]: ...\n'


def test_get_stub_params_one_builtin():
    code = code_template % {'params': 'i', 'ptypes': 'int', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int) -> None: ...\n'


def test_get_stub_params_two_builtin():
    code = code_template % {'params': 'i, s', 'ptypes': 'int, str', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int, s: str) -> None: ...\n'


def test_get_stub_params_imported():
    code = code_template % {'params': 'a', 'ptypes': 'A', 'rtype': 'None'}
    assert get_stub(code) == 'from x import A\n\n\ndef f(a: A) -> None: ...\n'


def test_get_stub_params_typing():
    code = code_template % {'params': 'l', 'ptypes': 'List', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import List\n\n\ndef f(l: List) -> None: ...\n'


def test_get_stub_params_typing_qualified():
    code = code_template % {'params': 'i, l', 'ptypes': 'int, List[str]', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import List\n\n\ndef f(i: int, l: List[str]) -> None: ...\n'


def test_get_stub_params_typing_qualified_multiple():
    code = code_template % {'params': 'i, d', 'ptypes': 'int, Dict[str, Any]', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import Any, Dict\n\n\ndef f(i: int, d: Dict[str, Any]) -> None: ...\n'


def test_get_stub_params_default_value():
    code = code_template % {'params': 's, i=0', 'ptypes': 'str, int', 'rtype': 'None'}
    assert get_stub(code) == 'def f(s: str, i: int = ...) -> None: ...\n'
