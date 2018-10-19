from pytest import fixture, mark, raises

import logging
import os
import shutil
import sys

from pkg_resources import get_distribution

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

    %(decorator)s
    def %(method)s(%(params)s):
        """Method

        :sig: (%(ptypes)s) -> None
        """
        self.a = a  # %(comment)s
'''


def test_get_stub_no_docstring():
    code = """def f():\n    pass\n"""
    assert get_stub(code) == ""


def test_get_stub_no_sig_in_docstring():
    code = '''def f():\n    """Func\n    """\n'''
    assert get_stub(code) == ""


def test_get_stub_two_functions_only_one_sig():
    code = (
        def_template % {"params": "", "ptypes": "", "rtype": "None"}
        + '''def g():\n    """Func\n    """\n'''
    )
    assert get_stub(code) == "def f() -> None: ...\n"


def test_get_stub_params_none_returns_none():
    code = def_template % {"params": "", "ptypes": "", "rtype": "None"}
    assert get_stub(code) == "def f() -> None: ...\n"


def test_get_stub_returns_builtin():
    code = def_template % {"params": "", "ptypes": "", "rtype": "int"}
    assert get_stub(code) == "def f() -> int: ...\n"


def test_get_stub_returns_imported():
    code = def_template % {"params": "", "ptypes": "", "rtype": "A"}
    assert get_stub(code) == "from x import A\n\ndef f() -> A: ...\n"


def test_get_stub_returns_dotted():
    code = def_template % {"params": "", "ptypes": "", "rtype": "r.s.T"}
    assert get_stub(code) == "import r.s\n\ndef f() -> r.s.T: ...\n"


def test_get_stub_returns_dotted_imported():
    code = def_template % {"params": "", "ptypes": "", "rtype": "A.X"}
    assert get_stub(code) == "from x import A\n\ndef f() -> A.X: ...\n"


def test_get_stub_returns_dotted_imported_relative():
    code = def_template % {"params": "", "ptypes": "", "rtype": "m.X"}
    assert get_stub(code) == "from . import m\n\ndef f() -> m.X: ...\n"


def test_get_stub_returns_typing():
    code = def_template % {"params": "", "ptypes": "", "rtype": "List"}
    assert get_stub(code) == "from typing import List\n\ndef f() -> List: ...\n"


def test_get_stub_returns_typing_qualified():
    code = def_template % {"params": "", "ptypes": "", "rtype": "List[str]"}
    assert get_stub(code) == "from typing import List\n\ndef f() -> List[str]: ...\n"


def test_get_stub_returns_typing_qualified_multiple():
    code = def_template % {"params": "", "ptypes": "", "rtype": "Dict[str, Any]"}
    assert get_stub(code) == "from typing import Any, Dict\n\ndef f() -> Dict[str, Any]: ...\n"


def test_get_stub_missing_name():
    code = def_template % {"params": "i", "ptypes": "foo", "rtype": "Dict[str, Any]"}
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Unknown types: foo" in str(e)


def test_get_stub_params_one_builtin():
    code = def_template % {"params": "i", "ptypes": "int", "rtype": "None"}
    assert get_stub(code) == "def f(i: int) -> None: ...\n"


def test_get_stub_params_two_builtin():
    code = def_template % {"params": "i, s", "ptypes": "int, str", "rtype": "None"}
    assert get_stub(code) == "def f(i: int, s: str) -> None: ...\n"


def test_get_stub_params_imported():
    code = def_template % {"params": "a", "ptypes": "A", "rtype": "None"}
    assert get_stub(code) == "from x import A\n\ndef f(a: A) -> None: ...\n"


def test_get_stub_params_dotted():
    code = def_template % {"params": "a", "ptypes": "x.A", "rtype": "None"}
    assert get_stub(code) == "import x\n\ndef f(a: x.A) -> None: ...\n"


def test_get_stub_params_dotted_imported():
    code = def_template % {"params": "a", "ptypes": "A.X", "rtype": "None"}
    assert get_stub(code) == "from x import A\n\ndef f(a: A.X) -> None: ...\n"


def test_get_stub_params_dotted_imported_relative():
    code = def_template % {"params": "a", "ptypes": "m.A", "rtype": "None"}
    assert get_stub(code) == "from . import m\n\ndef f(a: m.A) -> None: ...\n"


def test_get_stub_params_typing():
    code = def_template % {"params": "l", "ptypes": "List", "rtype": "None"}
    assert get_stub(code) == "from typing import List\n\ndef f(l: List) -> None: ...\n"


def test_get_stub_params_typing_qualified():
    code = def_template % {"params": "i, l", "ptypes": "int, List[str]", "rtype": "None"}
    assert (
        get_stub(code)
        == "from typing import List\n\ndef f(i: int, l: List[str]) -> None: ...\n"
    )


def test_get_stub_params_typing_qualified_multiple():
    code = def_template % {"params": "i, d", "ptypes": "int, Dict[str, Any]", "rtype": "None"}
    assert (
        get_stub(code)
        == "from typing import Any, Dict\n\ndef f(i: int, d: Dict[str, Any]) -> None: ...\n"
    )


def test_get_stub_params_typing_and_imported():
    code = def_template % {"params": "l, a", "ptypes": "List, A", "rtype": "None"}
    assert (
        get_stub(code)
        == "from typing import List\n\nfrom x import A\n\ndef f(l: List, a: A) -> None: ...\n"
    )


def test_get_stub_params_default_value():
    code = def_template % {"params": "s, i=0", "ptypes": "str, Optional[int]", "rtype": "None"}
    assert (
        get_stub(code)
        == "from typing import Optional\n\ndef f(s: str, i: Optional[int] = ...) -> None: ...\n"
    )


def test_get_stub_params_vararg():
    code = def_template % {"params": "i, *args", "ptypes": "int", "rtype": "None"}
    assert get_stub(code) == "def f(i: int, *args) -> None: ...\n"


def test_get_stub_params_kwargs():
    code = def_template % {"params": "i, **kwargs", "ptypes": "int", "rtype": "None"}
    assert get_stub(code) == "def f(i: int, **kwargs) -> None: ...\n"


def test_get_stub_params_vararg_and_kwargs():
    code = def_template % {"params": "i, *args, **kwargs", "ptypes": "int", "rtype": "None"}
    assert get_stub(code) == "def f(i: int, *args, **kwargs) -> None: ...\n"


@mark.skipif(sys.version_info < (3, 0), reason="syntax introduced in py3")
def test_get_stub_params_kwonly_args():
    code = def_template % {"params": "i, *, j", "ptypes": "int, int", "rtype": "None"}
    assert get_stub(code) == "def f(i: int, *, j: int) -> None: ...\n"


@mark.skipif(sys.version_info < (3, 0), reason="syntax introduced in py3")
def test_get_stub_params_kwonly_args_with_default():
    code = def_template % {
        "params": "i, *, j=0",
        "ptypes": "int, Optional[int]",
        "rtype": "None",
    }
    assert (
        get_stub(code)
        == "from typing import Optional\n\ndef f(i: int, *, j: Optional[int] = ...) -> None: ...\n"
    )


def test_get_stub_params_missing_types():
    code = def_template % {"params": "i, j", "ptypes": "int", "rtype": "None"}
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_get_stub_params_extra_types():
    code = def_template % {"params": "i", "ptypes": "int, int", "rtype": "None"}
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_get_stub_method_self():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    def m(self, a: int) -> None: ...\n"


def test_get_stub_bases_imported():
    code = class_template % {
        "bases": "(A)",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert (
        get_stub(code)
        == "from x import A\n\nclass C(A):\n    def m(self, a: int) -> None: ...\n"
    )


def test_get_stub_bases_dotted():
    code = class_template % {
        "bases": "(x.A)",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "import x\n\nclass C(x.A):\n    def m(self, a: int) -> None: ...\n"


def test_get_stub_bases_dotted_imported():
    code = class_template % {
        "bases": "(A.X)",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert (
        get_stub(code)
        == "from x import A\n\nclass C(A.X):\n    def m(self, a: int) -> None: ...\n"
    )


def test_get_stub_bases_dotted_imported_relative():
    code = class_template % {
        "bases": "(m.X)",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert (
        get_stub(code)
        == "from . import m\n\nclass C(m.X):\n    def m(self, a: int) -> None: ...\n"
    )


def test_get_stub_class_sig_to_init():
    temp = "\n".join([line for line in class_template.splitlines() if "sig" not in line])
    code = temp % {
        "bases": "",
        "doc": '"""Class\n\n    :sig: (str) -> None\n    """',
        "decorator": "",
        "method": "__init__",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    def __init__(self, a: str) -> None: ...\n"


def test_get_stub_class_sig_init_not_overwritten():
    code = class_template % {
        "bases": "",
        "doc": '"""Class\n\n    :sig: (str) -> None\n    """',
        "decorator": "",
        "method": "__init__",
        "params": "self, a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    def __init__(self, a: int) -> None: ...\n"


def test_get_stub_comment_module_variable_builtin():
    code = "n = 42  # sig: int\n"
    assert get_stub(code) == "n = ...  # type: int\n"


def test_get_stub_comment_module_variable_imported():
    code = "from x import A\n\nn = 42  # sig: A\n" ""
    assert get_stub(code) == "from x import A\n\nn = ...  # type: A\n"


def test_get_stub_comment_module_variable_dotted():
    code = "n = 42  # sig: x.A\n" ""
    assert get_stub(code) == "import x\n\nn = ...  # type: x.A\n"


def test_get_stub_comment_module_variable_dotted_imported():
    code = "from x import A\n\nn = 42  # sig: A.X\n" ""
    assert get_stub(code) == "from x import A\n\nn = ...  # type: A.X\n"


def test_get_stub_comment_module_variable_dotted_imported_relative():
    code = "from . import m\n\nn = 42  # sig: m.X\n" ""
    assert get_stub(code) == "from . import m\n\nn = ...  # type: m.X\n"


def test_get_stub_alias_comment():
    code = "# sigalias: B = int\n\nn = 42  # sig: B\n" ""
    assert get_stub(code) == "B = int\n\nn = ...  # type: B\n"


def test_get_stub_comment_instance_variable():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "",
        "method": "m",
        "params": "self, a",
        "ptypes": "int",
        "comment": "sig: str",
    }
    assert (
        get_stub(code)
        == "class C:\n    a = ...  # type: str\n    def m(self, a: int) -> None: ...\n"
    )


def test_get_stub_method_decorated_staticmethod():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "@staticmethod",
        "method": "m",
        "params": "a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    @staticmethod\n    def m(a: int) -> None: ...\n"


def test_get_stub_method_decorated_classmethod():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "@classmethod",
        "method": "m",
        "params": "cls, a",
        "ptypes": "int",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    @classmethod\n    def m(cls, a: int) -> None: ...\n"


def test_get_stub_method_property():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "@property",
        "method": "m",
        "params": "self",
        "ptypes": "",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    @property\n    def m(self) -> None: ...\n"


def test_get_stub_method_property_setter():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "@x.setter",
        "method": "m",
        "params": "self",
        "ptypes": "",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    @x.setter\n    def m(self) -> None: ...\n"


########################################
# command-line interface tests
########################################


@fixture
def source():
    base_dir = os.path.dirname(__file__)
    src = os.path.join(base_dir, "..", "pygenstub.py")
    dst = "/dev/shm/foo.py" if sys.platform in {"linux", "linux2"} else "foo.py"
    shutil.copy(src, dst)
    yield src, dst

    os.unlink(dst)
    if os.path.exists(dst + "i"):
        os.unlink(dst + "i")


def test_cli_help_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        main(argv=["pygenstub", "--help"])
    out, err = capsys.readouterr()
    assert out.startswith("usage: ")


def test_cli_version_should_print_version_number_and_exit(capsys):
    with raises(SystemExit):
        main(argv=["pygenstub", "--version"])
    out, err = capsys.readouterr()
    assert "pygenstub " + get_distribution("pygenstub").version + "\n" in {out, err}


def test_cli_no_input_file_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        main(argv=["pygenstub"])
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")
    assert ("required: source" in err) or ("too few arguments" in err)


def test_cli_unrecognized_arguments_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        main(argv=["pygenstub", "--foo", "foo.py"])
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")
    assert "unrecognized arguments: --foo" in err


def test_cli_debug_mode_should_print_debug_messages_on_stderr(caplog, source):
    caplog.set_level(logging.DEBUG)
    main(argv=["pygenstub", "--debug", source[1]])
    assert caplog.record_tuples[0][-1] == "running in debug mode"


def test_cli_original_module_should_generate_original_stub(source):
    main(argv=["pygenstub", source[1]])
    with open(source[0] + "i") as src:
        src_stub = src.read()
    with open(source[1] + "i") as dst:
        dst_stub = dst.read()
    assert dst_stub == src_stub
