from pytest import fixture, raises

import logging
import os
import shutil
import sys
from glob import glob
from tempfile import mkdtemp

import pygenstub


@fixture(scope="module", autouse=True)
def source_root():
    """Create source file hierarchy."""
    virtual_fs = "/dev/shm"
    if ("linux" in sys.platform) and os.path.exists(virtual_fs):
        root_dir = mkdtemp(dir=virtual_fs)
    else:
        root_dir = mkdtemp()

    example_file = os.path.join(os.path.dirname(__file__), "example.py")
    shutil.copyfile(example_file, os.path.join(root_dir, "example1.py"))
    shutil.copyfile(example_file, os.path.join(root_dir, "example2.py"))

    yield root_dir

    # shutil.rmtree(root_dir)


@fixture(autouse=True)
def clean_env(source_root):
    """Remove all generated stub files."""
    os.chdir(source_root)
    for stub in glob("*.pyi"):
        os.unlink(stub)
    if os.path.exists("typeshed"):
        shutil.rmtree("typeshed")


def test_help_should_print_usage(capsys):
    with raises(SystemExit):
        pygenstub.run(["pygenstub", "--help"])
    out, err = capsys.readouterr()
    assert out.startswith("usage: ")


def test_version_should_print_version_number(capsys):
    with raises(SystemExit):
        pygenstub.run(["pygenstub", "--version"])
    out, err = capsys.readouterr()
    out = out if sys.version_info >= (3,) else err
    assert out == "pygenstub %s\n" % pygenstub.__version__


def test_if_no_input_should_print_nothing(capsys):
    pygenstub.run(["pygenstub"])
    out, err = capsys.readouterr()
    assert (out == "") and (err == "")


def test_if_unrecognized_arguments_should_print_error(capsys):
    with raises(SystemExit):
        pygenstub.run(["pygenstub", "--foo", "example.py"])
    out, err = capsys.readouterr()
    assert "unrecognized arguments: --foo" in err


def test_if_in_debug_mode_should_log_debug_messages(caplog):
    caplog.set_level(logging.DEBUG)
    pygenstub.run(["pygenstub", "--debug", "example1.py"])
    assert "running in debug mode" in caplog.records[0].message


def test_single_input_file_should_produce_single_stub_file():
    assert not os.path.exists("example1.pyi")
    pygenstub.run(["pygenstub", "example1.py"])
    assert os.path.exists("example1.pyi")


def test_multiple_input_files_should_produce_multiple_stub_files():
    assert (not os.path.exists("example1.pyi")) and (not os.path.exists("example2.pyi"))
    pygenstub.run(["pygenstub", "example1.py", "example2.py"])
    assert os.path.exists("example1.pyi") and os.path.exists("example2.pyi")


def test_input_absolute_path_should_produce_stub_file_next_to_source(source_root):
    os.chdir(os.path.dirname(__file__))
    source = os.path.join(source_root, "example1.py")
    stub = os.path.join(source_root, "example1.pyi")
    assert not os.path.exists(stub)
    pygenstub.run(["pygenstub", os.path.abspath(source)])
    assert os.path.exists(stub)


def test_stub_file_should_be_saved_in_given_output_directory():
    assert not os.path.exists("typeshed")
    os.mkdir("typeshed")
    pygenstub.run(["pygenstub", "example1.py", "-o", "typeshed"])
    assert os.path.exists(os.path.join("typeshed", "example1.pyi"))


def test_output_directory_should_be_created_if_necessary():
    assert not os.path.exists("typeshed")
    pygenstub.run(["pygenstub", "example1.py", "-o", "typeshed"])
    assert os.path.exists(os.path.join("typeshed", "example1.pyi"))


def test_input_absolute_path_should_generate_stub_file_in_given_output_directory(source_root):
    os.chdir(os.path.dirname(__file__))
    source = os.path.join(source_root, "example1.py")
    out_dir = os.path.join(source_root, "typeshed")
    stub = os.path.join(out_dir + source_root, "example1.pyi")
    assert not os.path.exists(stub)
    pygenstub.run(["pygenstub", os.path.abspath(source), "-o", out_dir])
    assert os.path.exists(stub)


def test_module_stub_generation_should_print_error_if_no_output_directory_given(capsys):
    with raises(SystemExit):
        pygenstub.run(["pygenstub", "-m", "subprocess"])
    out, err = capsys.readouterr()
    assert "output directory is required" in err


def test_module_stub_generation_should_work_for_single_file_module():
    assert not os.path.exists(os.path.join("typeshed", "subprocess.pyi"))
    pygenstub.run(["pygenstub", "-m", "subprocess", "-o", "typeshed"])
    assert os.path.exists(os.path.join("typeshed", "subprocess.pyi"))


def test_module_stub_generation_should_work_for_multiple_file_module():
    assert not (os.path.exists(os.path.join("typeshed", "logging", "config.pyi"))) and (
        not os.path.exists(os.path.join("typeshed", "logging", "handlers.pyi"))
    )
    pygenstub.run(["pygenstub", "-m", "logging", "-o", "typeshed"])
    assert os.path.exists(os.path.join("typeshed", "logging", "config.pyi")) and os.path.exists(
        os.path.join("typeshed", "logging", "handlers.pyi")
    )
