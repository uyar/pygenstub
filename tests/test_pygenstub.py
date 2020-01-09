from pkg_resources import get_distribution

import pygenstub


def test_version_should_be_same_as_installed():
    assert get_distribution("pygenstub").version == pygenstub.__version__
