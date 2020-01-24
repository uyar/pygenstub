from pygenstub import get_mod_paths, get_pkg_paths


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
