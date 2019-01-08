from pytest import fixture, mark, raises

import logging
import os
import shutil
import sys
from io import StringIO

from pkg_resources import get_distribution

from pygenstub import __version__, get_stub, main


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


def get_function(name, desc="Foo", params=None, ptypes=None, rtype=None, decorators=None):
    code = StringIO()
    if decorators is not None:
        code.write("\n".join(decorators) + "\n")
    pstr = ", ".join(params) if params is not None else ""
    code.write("def %(name)s(%(p)s):\n" % {"name": name, "p": pstr})
    indent = " " * 4
    if desc:
        code.write(indent + '"""%(desc)s\n\n' % {"desc": desc})
        tstr = ", ".join(ptypes) if ptypes is not None else ""
        if rtype is not None:
            code.write(indent + ":sig: (%(t)s) -> %(rtype)s\n" % {"t": tstr, "rtype": rtype})
        code.write(indent + '"""\n')
    code.write(indent + "pass\n")
    return code.getvalue()


def test_version_should_be_same_as_installed():
    assert get_distribution("pygenstub").version == __version__


def test_if_no_docstring_then_stub_should_be_empty():
    code = get_function("f", desc="")
    assert get_stub(code) == ""


def test_if_no_sig_then_stub_should_be_empty():
    code = get_function("f")
    assert get_stub(code) == ""


def test_if_returns_none_then_stub_should_return_none():
    code = get_function("f", rtype="None")
    assert get_stub(code) == "def f() -> None: ...\n"


def test_if_returns_builtin_then_stub_should_return_builtin():
    code = get_function("f", rtype="int")
    assert get_stub(code) == "def f() -> int: ...\n"


def test_if_returns_from_imported_then_stub_should_include_import():
    code = "from x import A\n"
    code += "\n\n" + get_function("f", rtype="A")
    assert get_stub(code) == "from x import A\n\ndef f() -> A: ...\n"


def test_stub_should_exclude_unused_import():
    code = "from x import A, B\n"
    code += "\n\n" + get_function("f", rtype="A")
    assert get_stub(code) == "from x import A\n\ndef f() -> A: ...\n"


# def test_stub_should_include_all_used_imports():
#     code = "from x import A, B\n"
#     code += "\n\n" + get_function("f", rtype="A")
#     code += "\n\n" + get_function("g", rtype="B")
#     assert get_stub(code) == "from x import A, B\n\ndef f() -> A: ...\ndef g() -> B: ...\n"


def test_if_returns_imported_qualified_then_stub_should_include_import():
    code = "import x\n"
    code += "\n\n" + get_function("f", rtype="x.A")
    assert get_stub(code) == "import x\n\ndef f() -> x.A: ...\n"


def test_if_returns_from_imported_qualified_then_stub_should_include_import():
    code = "from x import y\n"
    code += "\n\n" + get_function("f", rtype="y.A")
    assert get_stub(code) == "from x import y\n\ndef f() -> y.A: ...\n"


def test_if_returns_module_imported_qualified_then_stub_should_include_import():
    code = "from x import y\n"
    code += get_function("f", rtype="y.A")
    assert get_stub(code) == "from x import y\n\ndef f() -> y.A: ...\n"


def test_if_returns_relative_imported_then_stub_should_include_import():
    code = "from . import x\n"
    code += "\n\n" + get_function("f", rtype="x.A")
    assert get_stub(code) == "from . import x\n\ndef f() -> x.A: ...\n"


def test_if_returns_unimported_qualified_then_stub_should_generate_import():
    code = get_function("f", rtype="x.y.A")
    assert get_stub(code) == "import x.y\n\ndef f() -> x.y.A: ...\n"


def test_if_returns_imported_typing_then_stub_should_include_import():
    code = "from typing import List\n"
    code += "\n\n" + get_function("f", rtype="List")
    assert get_stub(code) == "from typing import List\n\ndef f() -> List: ...\n"


def test_if_returns_unimported_typing_then_stub_should_generate_import():
    code = get_function("f", rtype="List")
    assert get_stub(code) == "from typing import List\n\ndef f() -> List: ...\n"


def test_if_returns_qualified_typing_then_stub_should_return_qualified_typing():
    code = get_function("f", rtype="List[str]")
    assert get_stub(code) == "from typing import List\n\ndef f() -> List[str]: ...\n"


def test_if_returns_multiple_typing_then_stub_should_generate_multiple_import():
    code = get_function("f", rtype="Dict[str, Any]")
    assert get_stub(code) == "from typing import Any, Dict\n\ndef f() -> Dict[str, Any]: ...\n"


def test_if_returns_unknown_type_should_raise_error():
    code = get_function("f", rtype="Foo")
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Unknown types: Foo" in str(e)


def test_if_one_param_then_stub_should_have_one_param():
    code = get_function("f", params=["i"], ptypes=["int"], rtype="None")
    assert get_stub(code) == "def f(i: int) -> None: ...\n"


def test_if_multiple_params_then_stub_should_have_multiple_params():
    code = get_function("f", params=["i", "s"], ptypes=["int", "str"], rtype="None")
    assert get_stub(code) == "def f(i: int, s: str) -> None: ...\n"


def test_if_param_type_imported_then_stub_should_include_import():
    code = "from x import A\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["A"], rtype="None")
    assert get_stub(code) == "from x import A\n\ndef f(a: A) -> None: ...\n"


def test_if_param_type_imported_qualified_then_stub_should_include_import():
    code = "import x\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["x.A"], rtype="None")
    assert get_stub(code) == "import x\n\ndef f(a: x.A) -> None: ...\n"


def test_if_param_type_from_imported_qualified_then_stub_should_include_import():
    code = "from x import A\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["A"], rtype="None")
    assert get_stub(code) == "from x import A\n\ndef f(a: A) -> None: ...\n"


def test_if_param_type_module_imported_qualified_then_stub_should_include_import():
    code = "from x import y\n"
    code += get_function("f", params=["a"], ptypes=["y.A"], rtype="None")
    assert get_stub(code) == "from x import y\n\ndef f(a: y.A) -> None: ...\n"


def test_if_param_type_relative_imported_qualified_then_stub_should_include_import():
    code = "from . import x\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["x.A"], rtype="None")
    assert get_stub(code) == "from . import x\n\ndef f(a: x.A) -> None: ...\n"


def test_if_param_type_unimported_qualified_then_stub_should_generate_import():
    code = get_function("f", params=["a"], ptypes=["x.y.A"], rtype="None")
    assert get_stub(code) == "import x.y\n\ndef f(a: x.y.A) -> None: ...\n"


def test_if_param_type_imported_typing_then_stub_should_include_import():
    code = "from typing import List\n"
    code += "\n\n" + get_function("f", params=["l"], ptypes=["List"], rtype="None")
    assert get_stub(code) == "from typing import List\n\ndef f(l: List) -> None: ...\n"


def test_if_param_type_unimported_typing_then_stub_should_include_import():
    code = get_function("f", params=["l"], ptypes=["List"], rtype="None")
    assert get_stub(code) == "from typing import List\n\ndef f(l: List) -> None: ...\n"


def test_if_param_type_qualified_typing_then_stub_should_include_qualified_typing():
    code = get_function("f", params=["ls"], ptypes=["List[str]"], rtype="None")
    assert get_stub(code) == "from typing import List\n\ndef f(ls: List[str]) -> None: ...\n"


def test_if_param_type_multiple_typing_then_stub_should_include_multiple_import():
    code = get_function("f", params=["d"], ptypes=["Dict[str, Any]"], rtype="None")
    assert (
        get_stub(code)
        == "from typing import Any, Dict\n\ndef f(d: Dict[str, Any]) -> None: ...\n"
    )


def test_if_param_type_unknown_should_raise_error():
    code = get_function("f", params=["i"], ptypes=["Foo"], rtype="None")
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Unknown types: Foo" in str(e)


def test_if_param_has_default_then_stub_should_include_ellipses():
    code = get_function("f", params=["i=0"], ptypes=["Optional[int]"], rtype="None")
    assert (
        get_stub(code)
        == "from typing import Optional\n\ndef f(i: Optional[int] = ...) -> None: ...\n"
    )


def test_stub_should_ignore_varargs_type():
    code = get_function("f", params=["i", "*args"], ptypes=["int"], rtype="None")
    assert get_stub(code) == "def f(i: int, *args) -> None: ...\n"


def test_stub_should_ignore_kwargs_type():
    code = get_function("f", params=["i", "**kwargs"], ptypes=["int"], rtype="None")
    assert get_stub(code) == "def f(i: int, **kwargs) -> None: ...\n"


def test_stub_should_ignore_vararg_and_kwargs_types():
    code = get_function("f", params=["i", "*args", "**kwargs"], ptypes=["int"], rtype="None")
    assert get_stub(code) == "def f(i: int, *args, **kwargs) -> None: ...\n"


@mark.skipif(sys.version_info < (3, 0), reason="syntax introduced in py3")
def test_stub_should_honor_kwonly_args():
    code = get_function("f", params=["i", "*", "j"], ptypes=["int", "int"], rtype="None")
    assert get_stub(code) == "def f(i: int, *, j: int) -> None: ...\n"


@mark.skipif(sys.version_info < (3, 0), reason="syntax introduced in py3")
def test_stub_should_honor_kwonly_args_with_default():
    code = get_function(
        "f", params=["i", "*", "j=0"], ptypes=["int", "Optional[int]"], rtype="None"
    )
    assert (
        get_stub(code)
        == "from typing import Optional\n\ndef f(i: int, *, j: Optional[int] = ...) -> None: ...\n"
    )


def test_missing_types_should_raise_error():
    code = get_function("f", params=["i", "j"], ptypes=["int"], rtype="None")
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_extra_types_should_raise_error():
    code = get_function("f", params=["i"], ptypes=["int", "int"], rtype="None")
    with raises(RuntimeError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_if_function_decorated_unknown_then_stub_should_ignore():
    code = get_function("f", rtype="None", decorators=["@foo"])
    assert get_stub(code) == "def f() -> None: ...\n"


def test_if_function_decorated_callable_unknown_then_stub_should_ignore():
    code = get_function("f", rtype="None", decorators=["@foo()"])
    assert get_stub(code) == "def f() -> None: ...\n"


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


def test_get_stub_method_decorated_unknown():
    code = class_template % {
        "bases": "",
        "doc": "",
        "decorator": "@foo",
        "method": "m",
        "params": "self",
        "ptypes": "",
        "comment": "",
    }
    assert get_stub(code) == "class C:\n    def m(self) -> None: ...\n"


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


def test_get_stub_method_decorated_property():
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


def test_get_stub_method_decorated_property_setter():
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


def test_stub_should_exclude_function_without_sig():
    code = get_function("f", rtype="None")
    code += "\n\n" + get_function("g", desc="")
    assert get_stub(code) == "def f() -> None: ...\n"


def test_get_stub_typing_import_should_come_first():
    code = "from x import A\n"
    code += "\n\n" + get_function("f", params=["a", "l"], ptypes=["A", "List"], rtype="None")
    assert (
        get_stub(code)
        == "from typing import List\n\nfrom x import A\n\ndef f(a: A, l: List) -> None: ...\n"
    )


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
    assert "pygenstub " + __version__ + "\n" in {out, err}


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
