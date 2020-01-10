from pytest import raises

import logging
import sys

import pygenstub


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
        pygenstub.run(["pygenstub", "--foo", "foo.py"])
    out, err = capsys.readouterr()
    assert "unrecognized arguments: --foo" in err


def test_if_in_debug_mode_should_log_debug_messages(caplog):
    caplog.set_level(logging.DEBUG)
    pygenstub.run(["pygenstub", "--debug", pygenstub.__file__])
    assert "running in debug mode" in caplog.records[0].message
