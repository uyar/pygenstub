# flake8: noqa

from __future__ import unicode_literals

from pytest import mark, raises

import sys
from io import StringIO

from pygenstub import get_stub


_INDENT = " " * 4


def get_function(
    name, desc="Do foo.", params=None, ptypes=None, rtype=None, decorators=None, body="pass"
):
    code = StringIO()
    if decorators is not None:
        code.write("\n".join(decorators) + "\n")
    pstr = ", ".join(params) if params is not None else ""
    code.write("def %(name)s(%(p)s):\n" % {"name": name, "p": pstr})
    if desc:
        code.write(_INDENT + '"""%(desc)s\n\n' % {"desc": desc})
        tstr = ", ".join(ptypes) if ptypes is not None else ""
        if rtype is not None:
            code.write(_INDENT + ":sig: (%(t)s) -> %(rtype)s\n" % {"t": tstr, "rtype": rtype})
        code.write(_INDENT + '"""\n')
    code.write(_INDENT + body + "\n")
    return code.getvalue()


def get_class(name, bases=None, desc="A foo.", sig=None, methods=None, classvars=None):
    code = StringIO()
    bstr = ("(" + ", ".join(bases) + ")") if bases is not None else ""
    code.write("class %(name)s%(bases)s:\n" % {"name": name, "bases": bstr})
    if desc is not None:
        code.write(_INDENT + '"""%(desc)s\n\n' % {"desc": desc})
        if sig is not None:
            code.write("\n" + _INDENT + ":sig: %(sig)s\n" % {"sig": sig})
    code.write(_INDENT + '"""\n')
    if classvars is not None:
        for classvar in classvars:
            code.write(_INDENT + classvar + "\n")
    if methods is not None:
        for method in methods:
            for line in method.splitlines():
                code.write(_INDENT + line + "\n")
    else:
        code.write(_INDENT + "pass\n")
    return code.getvalue()


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


def test_if_returns_from_as_imported_then_stub_should_include_import():
    code = "from x import A as B\n"
    code += "\n\n" + get_function("f", rtype="B")
    assert get_stub(code) == "from x import A as B\n\ndef f() -> B: ...\n"


def test_stub_should_exclude_unused_import():
    code = "from x import A, B\n"
    code += "\n\n" + get_function("f", rtype="A")
    assert get_stub(code) == "from x import A\n\ndef f() -> A: ...\n"


def test_if_returns_imported_qualified_then_stub_should_include_import():
    code = "import x\n"
    code += "\n\n" + get_function("f", rtype="x.A")
    assert get_stub(code) == "import x\n\ndef f() -> x.A: ...\n"


def test_if_returns_as_imported_qualified_then_stub_should_include_import():
    code = "import x as y\n"
    code += "\n\n" + get_function("f", rtype="y.A")
    assert get_stub(code) == "import x as y\n\ndef f() -> y.A: ...\n"


def test_if_returns_from_imported_qualified_then_stub_should_include_import():
    code = "from x import y\n"
    code += "\n\n" + get_function("f", rtype="y.A")
    assert get_stub(code) == "from x import y\n\ndef f() -> y.A: ...\n"


def test_if_returns_relative_imported_qualified_then_stub_should_include_import():
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
    with raises(ValueError) as e:
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


def test_if_param_type_from_imported_then_stub_should_include_import():
    code = "from x import A\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["A"], rtype="None")
    assert get_stub(code) == "from x import A\n\ndef f(a: A) -> None: ...\n"


def test_if_param_type_imported_qualified_then_stub_should_include_import():
    code = "import x\n"
    code += "\n\n" + get_function("f", params=["a"], ptypes=["x.A"], rtype="None")
    assert get_stub(code) == "import x\n\ndef f(a: x.A) -> None: ...\n"


def test_if_param_type_from_imported_qualified_then_stub_should_include_import():
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
    with raises(ValueError) as e:
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
    with raises(ValueError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_extra_types_should_raise_error():
    code = get_function("f", params=["i"], ptypes=["int", "int"], rtype="None")
    with raises(ValueError) as e:
        get_stub(code)
    assert "Parameter names and types don't match: " in str(e)


def test_if_function_decorated_unknown_then_stub_should_ignore():
    code = get_function("f", rtype="None", decorators=["@foo"])
    assert get_stub(code) == "def f() -> None: ...\n"


def test_if_function_decorated_callable_unknown_then_stub_should_ignore():
    code = get_function("f", rtype="None", decorators=["@foo()"])
    assert get_stub(code) == "def f() -> None: ...\n"


def test_stub_should_include_empty_class():
    code = get_class("C")
    assert get_stub(code) == "class C: ...\n"


def test_method_stub_should_include_self():
    method = get_function("m", params=["self"], rtype="None")
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    def m(self) -> None: ...\n"


def test_method_stub_should_include_params():
    method = get_function("m", params=["self", "i"], ptypes=["int"], rtype="None")
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    def m(self, i: int) -> None: ...\n"


def test_if_base_builtin_then_stub_should_include_base():
    code = get_class("C", bases=["dict"])
    assert get_stub(code) == "class C(dict): ...\n"


def test_if_base_from_imported_then_stub_should_include_import():
    code = "from x import A\n"
    code += "\n\n" + get_class("C", bases=["A"])
    assert get_stub(code) == "from x import A\n\nclass C(A): ...\n"


def test_if_base_imported_qualified_then_stub_should_include_import():
    code = "import x\n"
    code += "\n\n" + get_class("C", bases=["x.A"])
    assert get_stub(code) == "import x\n\nclass C(x.A): ...\n"


def test_if_base_from_imported_qualified_then_stub_should_include_import():
    code = "from x import y\n"
    code += "\n\n" + get_class("C", bases=["y.A"])
    assert get_stub(code) == "from x import y\n\nclass C(y.A): ...\n"


def test_if_base_unimported_qualified_then_stub_should_generate_import():
    code = get_class("C", bases=["x.y.A"])
    assert get_stub(code) == "import x.y\n\nclass C(x.y.A): ...\n"


def test_if_base_relative_imported_qualified_then_stub_should_include_import():
    code = "from . import x\n"
    code += "\n\n" + get_class("C", bases=["x.A"])
    assert get_stub(code) == "from . import x\n\nclass C(x.A): ...\n"


def test_class_sig_should_be_moved_to_init_method():
    method = get_function("__init__", params=["self", "x"], rtype=None)
    code = get_class("C", sig="(str) -> int", methods=[method])
    assert get_stub(code) == "class C:\n    def __init__(self, x: str) -> int: ...\n"


def test_class_sig_should_not_overwrite_existing_init_sig():
    method = get_function("__init__", params=["self", "x"], ptypes=["int"], rtype="None")
    code = get_class("C", sig="(str) -> int", methods=[method])
    assert get_stub(code) == "class C:\n    def __init__(self, x: int) -> None: ...\n"


def test_if_method_decorated_unknown_then_stub_should_ignore():
    method = get_function("m", params=["self"], rtype="None", decorators=["@foo"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    def m(self) -> None: ...\n"


def test_if_method_decorated_callable_unknown_then_stub_should_ignore():
    method = get_function("m", params=["self"], rtype="None", decorators=["@foo()"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    def m(self) -> None: ...\n"


def test_if_method_decorated_staticmethod_then_stub_should_include_decorator():
    method = get_function("m", rtype="None", decorators=["@staticmethod"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    @staticmethod\n    def m() -> None: ...\n"


def test_if_method_decorated_classmethod_then_stub_should_include_decorator():
    method = get_function("m", params=["cls"], rtype="None", decorators=["@classmethod"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    @classmethod\n    def m(cls) -> None: ...\n"


def test_if_method_decorated_property_then_stub_should_include_decorator():
    method = get_function("m", params=["self"], rtype="None", decorators=["@property"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    @property\n    def m(self) -> None: ...\n"


def test_if_method_decorated_property_setter_then_stub_should_include_decorator():
    method = get_function("m", params=["self"], rtype="None", decorators=["@x.setter"])
    code = get_class("C", methods=[method])
    assert get_stub(code) == "class C:\n    @x.setter\n    def m(self) -> None: ...\n"


def test_module_variable_type_comment_builtin_should_be_ellipsized():
    code = "n = 42  # sig: int\n"
    assert get_stub(code) == "n = ...  # type: int\n"


def test_module_variable_type_comment_from_imported_should_include_import():
    code = "from x import A\n\nn = 42  # sig: A\n" ""
    assert get_stub(code) == "from x import A\n\nn = ...  # type: A\n"


def test_module_variable_type_comment_imported_qualified_should_include_import():
    code = "import x\n\nn = 42  # sig: x.A\n" ""
    assert get_stub(code) == "import x\n\nn = ...  # type: x.A\n"


def test_module_variable_type_comment_relative_qualified_should_include_import():
    code = "from . import x\n\nn = 42  # sig: x.A\n" ""
    assert get_stub(code) == "from . import x\n\nn = ...  # type: x.A\n"


def test_module_variable_type_comment_unimported_qualified_should_include_import():
    code = "n = 42  # sig: x.y.A\n" ""
    assert get_stub(code) == "import x.y\n\nn = ...  # type: x.y.A\n"


def test_get_stub_comment_class_variable():
    code = get_class("C", classvars=["a = 42  # sig: int"])
    assert get_stub(code) == "class C:\n    a = ...  # type: int\n"


def test_get_stub_comment_instance_variable():
    method = get_function("m", params=["self"], rtype="None", body="self.a = 42  # sig: int")
    code = get_class("C", methods=[method])
    assert (
        get_stub(code) == "class C:\n    a = ...  # type: int\n    def m(self) -> None: ...\n"
    )


def test_stub_should_use_alias_comment():
    code = "# sigalias: B = int\n\nn = 42  # sig: B\n" ""
    assert get_stub(code) == "B = int\n\nn = ...  # type: B\n"


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
