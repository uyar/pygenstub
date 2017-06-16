from pytest import fixture, raises

import os
import shutil

from pygenstub import get_stub, main


def_template = '''
from x import A, B
from . import m


def f(%(params)s):
    """Func

    :sig: (%(ptypes)s) -> %(rtype)s
    """
'''

class_template = '''
from x import A
from . import m


class C%(bases)s:
    %(doc)s

    def %(method)s(self, a):
        """Method

        :sig: (int) -> None
        """
        self.a = a  # %(comment)s
'''


def test_get_stub_no_docstring():
    code = '''def f():\n    pass\n'''
    assert get_stub(code) == ''


def test_get_stub_no_sig_in_docstring():
    code = '''def f():\n    """Func\n    """\n'''
    assert get_stub(code) == ''


def test_get_stub_two_functions_only_one_sig():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'None'} + \
           '''def g():\n    """Func\n    """\n'''
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_params_none_returns_none():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'None'}
    assert get_stub(code) == 'def f() -> None: ...\n'


def test_get_stub_returns_builtin():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'int'}
    assert get_stub(code) == 'def f() -> int: ...\n'


def test_get_stub_returns_imported():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'A'}
    assert get_stub(code) == 'from x import A\n\n\ndef f() -> A: ...\n'


def test_get_stub_returns_dotted():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'r.s.T'}
    assert get_stub(code) == 'import r.s\n\n\ndef f() -> r.s.T: ...\n'


def test_get_stub_returns_dotted_imported():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'A.X'}
    assert get_stub(code) == 'from x import A\n\n\ndef f() -> A.X: ...\n'


def test_get_stub_returns_dotted_imported_relative():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'm.X'}
    assert get_stub(code) == 'from . import m\n\n\ndef f() -> m.X: ...\n'


def test_get_stub_returns_typing():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'List'}
    assert get_stub(code) == 'from typing import List\n\n\n' + \
        'def f() -> List: ...\n'


def test_get_stub_returns_typing_qualified():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'List[str]'}
    assert get_stub(code) == 'from typing import List\n\n\n' + \
        'def f() -> List[str]: ...\n'


def test_get_stub_returns_typing_qualified_multiple():
    code = def_template % {'params': '', 'ptypes': '', 'rtype': 'Dict[str, Any]'}
    assert get_stub(code) == 'from typing import Any, Dict\n\n\n' + \
        'def f() -> Dict[str, Any]: ...\n'


def test_get_stub_params_one_builtin():
    code = def_template % {'params': 'i', 'ptypes': 'int', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int) -> None: ...\n'


def test_get_stub_params_two_builtin():
    code = def_template % {'params': 'i, s', 'ptypes': 'int, str', 'rtype': 'None'}
    assert get_stub(code) == 'def f(i: int, s: str) -> None: ...\n'


def test_get_stub_params_imported():
    code = def_template % {'params': 'a', 'ptypes': 'A', 'rtype': 'None'}
    assert get_stub(code) == 'from x import A\n\n\ndef f(a: A) -> None: ...\n'


def test_get_stub_params_dotted():
    code = def_template % {'params': 'a', 'ptypes': 'x.A', 'rtype': 'None'}
    assert get_stub(code) == 'import x\n\n\ndef f(a: x.A) -> None: ...\n'


def test_get_stub_params_dotted_imported():
    code = def_template % {'params': 'a', 'ptypes': 'A.X', 'rtype': 'None'}
    assert get_stub(code) == 'from x import A\n\n\ndef f(a: A.X) -> None: ...\n'


def test_get_stub_params_dotted_imported_relative():
    code = def_template % {'params': 'a', 'ptypes': 'm.A', 'rtype': 'None'}
    assert get_stub(code) == 'from . import m\n\n\ndef f(a: m.A) -> None: ...\n'


def test_get_stub_params_typing():
    code = def_template % {'params': 'l', 'ptypes': 'List', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import List\n\n\n' + \
        'def f(l: List) -> None: ...\n'


def test_get_stub_params_typing_qualified():
    code = def_template % {'params': 'i, l', 'ptypes': 'int, List[str]', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import List\n\n\n' + \
        'def f(i: int, l: List[str]) -> None: ...\n'


def test_get_stub_params_typing_qualified_multiple():
    code = def_template % {'params': 'i, d', 'ptypes': 'int, Dict[str, Any]', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import Any, Dict\n\n\n' + \
        'def f(i: int, d: Dict[str, Any]) -> None: ...\n'


def test_get_stub_params_default_value():
    code = def_template % {'params': 's, i=0', 'ptypes': 'str, Optional[int]', 'rtype': 'None'}
    assert get_stub(code) == 'from typing import Optional\n\n\n' + \
        'def f(s: str, i: Optional[int] = ...) -> None: ...\n'


def test_get_stub_method_self():
    code = class_template % {'bases': '', 'doc': '', 'method': 'm', 'comment': ''}
    assert get_stub(code) == 'class C:\n    def m(self, a: int) -> None: ...\n'


def test_get_stub_bases_imported():
    code = class_template % {'bases': '(A)', 'doc': '', 'method': 'm', 'comment': ''}
    assert get_stub(code) == 'from x import A\n\n\n' + \
        'class C(A):\n    def m(self, a: int) -> None: ...\n'


def test_get_stub_bases_dotted():
    code = class_template % {'bases': '(x.A)', 'doc': '', 'method': 'm', 'comment': ''}
    assert get_stub(code) == 'import x\n\n\n' + \
        'class C(x.A):\n    def m(self, a: int) -> None: ...\n'


def test_get_stub_bases_dotted_imported():
    code = class_template % {'bases': '(A.X)', 'doc': '', 'method': 'm', 'comment': ''}
    assert get_stub(code) == 'from x import A\n\n\n' + \
        'class C(A.X):\n    def m(self, a: int) -> None: ...\n'


def test_get_stub_bases_dotted_imported_relative():
    code = class_template % {'bases': '(m.X)', 'doc': '', 'method': 'm', 'comment': ''}
    assert get_stub(code) == 'from . import m\n\n\n' + \
        'class C(m.X):\n    def m(self, a: int) -> None: ...\n'


def test_get_stub_class_sig_to_init():
    temp = '\n'.join([line for line in class_template.splitlines()
                      if 'sig' not in line])
    code = temp % {'bases': '',
                   'doc': '"""Class\n\n    :sig: (str) -> None\n    """',
                   'method': '__init__',
                   'comment': ''}
    assert get_stub(code) == 'class C:\n    def __init__(self, a: str) -> None: ...\n'


def test_get_stub_class_sig_init_not_overwritten():
    code = class_template % {'bases': '',
                             'doc': '"""Class\n\n    :sig: (str) -> None\n    """',
                             'method': '__init__',
                             'comment': ''}
    assert get_stub(code) == 'class C:\n    def __init__(self, a: int) -> None: ...\n'


def test_get_stub_comment_module_variable_builtin():
    code = 'n = 42  # sig: int\n'
    assert get_stub(code) == 'n = ...  # type: int\n'


def test_get_stub_comment_module_variable_imported():
    code = 'from x import A\n\nn = 42  # sig: A\n'''
    assert get_stub(code) == 'from x import A\n\n\nn = ...  # type: A\n'


def test_get_stub_comment_module_variable_dotted():
    code = 'n = 42  # sig: x.A\n'''
    assert get_stub(code) == 'import x\n\n\nn = ...  # type: x.A\n'


def test_get_stub_comment_module_variable_dotted_imported():
    code = 'from x import A\n\nn = 42  # sig: A.X\n'''
    assert get_stub(code) == 'from x import A\n\n\nn = ...  # type: A.X\n'


def test_get_stub_comment_module_variable_dotted_imported_relative():
    code = 'from . import m\n\nn = 42  # sig: m.X\n'''
    assert get_stub(code) == 'from . import m\n\n\nn = ...  # type: m.X\n'


def test_get_stub_comment_instance_variable():
    code = class_template % {'bases': '', 'doc': '', 'method': 'm', 'comment': 'sig: str'}
    assert get_stub(code) == 'class C:\n    a = ...  # type: str\n\n' + \
        '    def m(self, a: int) -> None: ...\n'


########################################
# command-line interface tests
########################################


@fixture()
def source():
    base_dir = os.path.dirname(__file__)
    src = os.path.join(base_dir, '..', 'pygenstub.py')
    dst = 'foo.py'
    shutil.copy(src, dst)
    yield src, dst
    os.unlink(dst)
    os.unlink(dst + 'i')


def test_cli_help_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        main(argv=['pygenstub', '--help'])
    out, err = capsys.readouterr()
    assert out.startswith('usage: ')


def test_cli_no_input_file_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        main(argv=['pygenstub'])
    out, err = capsys.readouterr()
    assert err.startswith('usage: ')
    assert ('required: source' in err) or ('too few arguments' in err)


def test_cli_original_module_should_generate_original_stub(source):
    main(argv=['pygenstub', source[1]])
    with open(source[0] + 'i') as src:
        src_stub = src.read()
    with open(source[1] + 'i') as dst:
        dst_stub = dst.read()
    assert dst_stub == src_stub
