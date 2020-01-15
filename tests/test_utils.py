from pytest import raises

from pygenstub import extract_signature, get_mod_paths, get_pkg_paths, parse_signature


def test_extract_signature_should_return_value_of_sig_field():
    assert extract_signature("foo\n\n:sig: () -> None\n:param a: b\n") == "() -> None"


def test_extract_signature_should_return_none_if_no_sig_field():
    assert extract_signature("foo\n\n:param a: b\n") is None


def test_extract_signature_should_fail_if_multiple_sig_fields():
    with raises(ValueError):
        extract_signature("foo\n\n:sig: () -> None\n:sig: () -> None\n")


def test_parse_signature_should_return_input_types_return_type_and_required_types():
    assert parse_signature("(str) -> int") == (["str"], "int", {"str", "int"})


def test_parse_signature_should_return_multiple_input_types_in_sequence():
    assert parse_signature("(str, bool) -> int")[0] == ["str", "bool"]


def test_parse_signature_should_return_all_input_types_if_duplicates():
    assert parse_signature("(str, str) -> int")[0] == ["str", "str"]


def test_parse_signature_should_treat_bracketed_types_as_a_unit():
    assert parse_signature("(List[str]) -> int")[0] == ["List[str]"]


def test_parse_signature_should_treat_bracketed_csv_types_as_a_unit():
    assert parse_signature("(int, Tuple[str, int]) -> int")[0] == ["int", "Tuple[str, int]"]


def test_parse_signature_should_treat_nested_bracketed_types_as_a_unit():
    assert parse_signature("(int, Optional[Tuple[str, int]], str) -> int")[0] == [
        "int",
        "Optional[Tuple[str, int]]",
        "str",
    ]


def test_parse_signature_should_return_empty_input_types_if_no_input_parameters():
    assert parse_signature("() -> int")[0] == []


def test_parse_signature_should_accept_none_as_a_type():
    assert parse_signature("() -> None") == ([], "None", {"None"})


def test_parse_signature_should_return_non_duplicated_required_types():
    assert parse_signature("(str, str) -> int")[2] == {"str", "int"}


def test_parse_signature_should_consider_components_of_bracketed_types_as_separate():
    assert parse_signature("(str, List[str]) -> None")[2] == {"str", "List", "None"}


def test_parse_signature_should_consider_components_of_nested_bracketed_types_as_separate():
    assert parse_signature("(int, Optional[Tuple[str, int]], str) -> Tuple[int, bool]")[2] == {
        "int",
        "Optional",
        "Tuple",
        "str",
        "bool",
    }


def test_parse_signature_should_treat_signature_as_variable_type_comment_if_no_arrow():
    assert parse_signature("int") == (None, "int", {"int"})


def test_get_mod_source_should_return_python_file_path():
    assert get_mod_paths("subprocess")[0].name == "subprocess.py"


def test_get_mod_source_should_return_none_if_module_not_found():
    assert get_mod_paths("foo") is None


def test_get_mod_source_should_return_none_if_source_is_not_python():
    assert get_mod_paths("math") is None


def test_get_pkg_sources_should_return_python_file_paths():
    assert [p[0].name for p in get_pkg_paths("logging")] == ["config.py", "handlers.py"]


def test_get_pkg_sources_should_return_python_mod_path_for_single_file_package():
    assert [p[0].name for p in get_pkg_paths("subprocess")] == ["subprocess.py"]


def test_get_pkg_sources_should_return_empty_list_if_module_not_found():
    assert get_pkg_paths("foo") == []


def test_get_pkg_sources_should_return_empty_list_if_no_python_sources_found():
    assert get_pkg_paths("math") == []
