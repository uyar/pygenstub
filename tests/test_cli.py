from pytest import fixture

import subprocess
import sys

if sys.version_info < (3, 5):
    from pathlib2 import Path
else:
    from pathlib import Path

import pygenstub


@fixture
def source():
    """Python source code for testing."""
    src = Path(__file__).parent.parent / "pygenstub.py"
    dst = (
        Path("/dev", "shm", "foo.py") if sys.platform in {"linux", "linux2"} else Path("foo.py")
    )
    Path(dst).write_bytes(Path(src).read_bytes())
    yield str(src), str(dst)

    dst.unlink()
    dst.with_suffix(".pyi").unlink()


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


def test_debug_mode_should_print_debug_messages_on_stderr(capfd, source):
    subprocess.call([sys.executable, "-m", "pygenstub", "--debug", source[1]])
    out, err = capfd.readouterr()
    assert "running in debug mode" in err


def test_original_module_should_generate_original_stub(source):
    subprocess.call([sys.executable, "-m", "pygenstub", source[1]])
    with open(source[0] + "i") as src:
        src_stub = src.read()
    with open(source[1] + "i") as dst:
        dst_stub = dst.read()
    assert dst_stub == src_stub
