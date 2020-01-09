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


def test_version_should_print_version_number_and_exit(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub", "--version"])
    out, err = capfd.readouterr()
    assert "pygenstub " + pygenstub.__version__ + "\n" in {out, err}


def test_no_input_should_do_nothing(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub"])
    out, err = capfd.readouterr()
    assert out == ""


def test_unrecognized_arguments_should_print_usage_and_exit(capfd):
    subprocess.call([sys.executable, "-m", "pygenstub", "--foo", "foo.py"])
    out, err = capfd.readouterr()
    assert err.startswith("usage: ")
    assert "unrecognized arguments: --foo" in err


def test_debug_mode_should_print_debug_messages_on_stderr(capfd):
    source = Path(__file__).with_name("example.py")
    subprocess.call([sys.executable, "-m", "pygenstub", "--debug", str(source)])
    out, err = capfd.readouterr()
    assert "running in debug mode" in err.splitlines()[0]


def test_original_module_should_generate_original_stub():
    subprocess.call([sys.executable, "-m", "pygenstub", pygenstub.__file__])
    assert (
        Path(pygenstub.__file__).with_suffix(".pyi").read_bytes()
        == Path("pygenstub.pyi").read_bytes()
    )
