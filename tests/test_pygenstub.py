from pygenstub import get_stub


code_template = '''
from x import A, B

def f(%(params)s):
    """Func

    :signature: (%(ptypes)s) -> %(rtype)s
    """
'''


def test_get_stub_no_docstring():
    code = '''def f():\n    pass\n'''
    assert get_stub(code) == ''


def test_get_stub_no_signature():
    code = '''def f():\n    """Func\n    """\n'''
    assert get_stub(code) == ''


def test_get_stub_missing_signature():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'None'} + \
           '''def g():\n    """Func\n    """\n'''
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_params_none_returns_none():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'None'}
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_params_one_builtin_returns_none():
    code = code_template % {'params': 'i', 'ptypes': 'int', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int) -> None: ...\n'


def test_get_stub_params_none_returns_builtin():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'int'}
    assert get_stub(code) == 'def f() -> int: ...\n'


def test_get_stub_params_two_builtin_returns_none():
    code = code_template % {'params': 'i, s', 'ptypes': 'int, str', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int, s: str) -> None: ...\n'


def test_get_stub_params_one_imported_returns_none():
    code = code_template % {'params': 'x', 'ptypes': 'A', 'rtype': 'None'}
    assert get_stub(code) == 'from x import A\n\n\ndef f(x: A) -> None: ...\n'


def test_get_stub_params_none_returns_imported():
    code = code_template % {'params': '', 'ptypes': '', 'rtype': 'A'}
    assert get_stub(code) == 'from x import A\n\n\ndef f() -> A: ...\n'
