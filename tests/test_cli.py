# flake8: noqa

from pytest import fixture, raises

import logging
import os
import shutil
import sys

from pkg_resources import get_distribution

import pygenstub


@fixture
def source():
    """Python source code for testing."""
    base_dir = os.path.dirname(__file__)
    src = os.path.join(base_dir, "..", "pygenstub.py")
    dst = "/dev/shm/foo.py" if sys.platform in {"linux", "linux2"} else "foo.py"
    shutil.copy(src, dst)
    yield src, dst

    os.unlink(dst)
    if os.path.exists(dst + "i"):
        os.unlink(dst + "i")


def test_version_should_be_same_as_installed():
    assert get_distribution("pygenstub").version == pygenstub.__version__


def test_cli_help_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        pygenstub.main(argv=["pygenstub", "--help"])
    out, err = capsys.readouterr()
    assert out.startswith("usage: ")


def test_cli_version_should_print_version_number_and_exit(capsys):
    with raises(SystemExit):
        pygenstub.main(argv=["pygenstub", "--version"])
    out, err = capsys.readouterr()
    assert "pygenstub " + pygenstub.__version__ + "\n" in {out, err}


def test_cli_no_input_should_do_nothing(capsys):
    pygenstub.main(argv=["pygenstub"])
    out, err = capsys.readouterr()
    assert out == ""


def test_cli_unrecognized_arguments_should_print_usage_and_exit(capsys):
    with raises(SystemExit):
        pygenstub.main(argv=["pygenstub", "--foo", "foo.py"])
    out, err = capsys.readouterr()
    assert err.startswith("usage: ")
    assert "unrecognized arguments: --foo" in err


def test_cli_debug_mode_should_print_debug_messages_on_stderr(caplog, source):
    caplog.set_level(logging.DEBUG)
    pygenstub.main(argv=["pygenstub", "--debug", source[1]])
    assert caplog.record_tuples[0][-1] == "running in debug mode"


def test_cli_original_module_should_generate_original_stub(source):
    pygenstub.main(argv=["pygenstub", source[1]])
    with open(source[0] + "i") as src:
        src_stub = src.read()
    with open(source[1] + "i") as dst:
        dst_stub = dst.read()
    assert dst_stub == src_stub
