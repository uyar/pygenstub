from pygenstub import get_mod_source, get_pkg_sources


def test_get_mod_source_should_return_python_file_path():
    assert get_mod_source("re").name == "re.py"


def test_get_mod_source_should_return_none_if_module_not_found():
    assert get_mod_source("foo") is None


def test_get_mod_source_should_return_none_if_source_is_not_python():
    assert get_mod_source("math") is None


def test_get_pkg_sources_should_return_python_file_paths():
    assert [p.name for p in get_pkg_sources("logging")] == ["config.py", "handlers.py"]


def test_get_pkg_sources_should_return_python_mod_path_for_single_file_package():
    assert [p.name for p in get_pkg_sources("re")] == ["re.py"]


def test_get_pkg_sources_should_return_empty_list_if_module_not_found():
    assert get_pkg_sources("foo") == []


def test_get_pkg_sources_should_return_empty_list_if_no_python_sources_found():
    assert get_pkg_sources("math") == []
