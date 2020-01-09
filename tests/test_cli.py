import subprocess
import sys

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

import pygenstub


def test_help_should_print_usage(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub", "--help"])
    out, err = capfd.readouterr()
    assert out.startswith("usage: ")


def test_version_should_print_version_number(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub", "--version"])
    out, err = capfd.readouterr()
    out = out if sys.version_info >= (3,) else err
    assert out == "pygenstub %s\n" % pygenstub.__version__


def test_if_no_input_should_print_nothing(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub"])
    out, err = capfd.readouterr()
    assert out == ""


def test_if_unrecognized_arguments_should_print_error(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub", "--foo", "foo.py"])
    out, err = capfd.readouterr()
    assert "unrecognized arguments: --foo" in err


def test_if_in_debug_mode_should_print_debug_messages_on_stderr(capfd):
    source = Path(__file__).with_name("example.py")
    subprocess.call([sys.executable, "-m", "pygenstub", "--debug", str(source)])
    out, err = capfd.readouterr()
    assert "running in debug mode" in err.splitlines()[0]
