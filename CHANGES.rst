Changes
=======

2.0.2 (unreleased)
------------------

- Drop support for Python 3.6.

2.0.1 (2021-02-13)
------------------

- Fix signature alias parsing.

2.0.0 (2021-02-13)
------------------

- Drop support for Python 2, 3.4, and 3.5.
- Generate PEP-526 style variable annotations.
- Support type annotations for ``*args`` and ``**kwargs``.

1.4.1 (2020-01-13)
------------------

- Fix error when input path is absolute and an output directory is given.

1.4.0 (2019-03-27)
------------------

- Generate stubs for multiple input files.
- Generate stubs for directories.
- Generate stubs for modules.
- Add option for storing stub files in an output directory.
- Add option to generate generic stubs.

1.3.0 (2019-03-07)
------------------

- Support names renamed with as during import.
- Support class variables.

1.2.4 (2019-02-01)
------------------

- More spacing fixes for consecutive class stubs.

1.2.3 (2019-01-31)
------------------

- Improve layout for stub generation with one-line class stubs.

1.2.2 (2019-01-08)
------------------

- Fix stub generation for superclass declarations with multiple dots.

1.2.1 (2018-12-27)
------------------

- Fix problem with function decorators that have parameters.
- Switch to poetry for project management.

1.2 (2018-10-19)
----------------

- Generate stub files that follow the same layout as Black.
- Fixed stub generation for async functions with decorators.

1.1 (2018-05-25)
----------------

- Added support for generating async function stubs.

1.0 (2018-05-25)
----------------

- Include type alias expansion in parameter type docstring.

1.0b9 (2018-03-23)
------------------

- Fixed bug about missing newlines after type aliases.

1.0b8 (2018-03-23)
------------------

- Added simplistic support for defining type aliases.

1.0b7 (2018-01-18)
------------------

- Added support for getting class signature from init method in Sphinx.

1.0b6 (2017-07-26)
------------------

- Fixed handling of * separator for keyword-only arguments.
- Added support for keyword-only arguments with default values.
- Added --version option to command line arguments.

1.0b5 (2017-07-26)
------------------

- Added support for property, staticmethod, and classmethod decorators.
- Added support for keyword-only arguments.

1.0b4 (2017-06-16)
------------------

- Collect builtin types from the builtins module.

1.0b3 (2017-06-16)
------------------

- Fixes for ``*args`` and ``**kwargs`` on Python 2 code.

1.0b2 (2017-05-26)
------------------

- Added support for Python 2 again.

1.0b1 (2017-05-09)
------------------

- Added support for using type hints in Sphinx autodoc.

1.0a6 (2017-03-06)
------------------

- Improvements on imported names.

1.0a5 (2017-02-07)
------------------

- Support for methods.
- Support for instance variables.
- Support for base classes.
- Shortened the field name from "signature" to "sig".
- Use three dots instead of actual value for parameter defaults.
- Dropped support for Python 2.

1.0a4 (2017-01-06)
------------------

- Long stubs are now spread over multiple lines.
- Better handling of parameter defaults that are tuples.
- Bugfix: handling of parameter defaults that have the value None.

1.0a3 (2017-01-06)
------------------

- Proper support for names from the typing module in input parameters.
- Added parameter default values to stubs.

1.0a2 (2017-01-03)
------------------

- Support for Python 2.7.

1.0a1 (2017-01-03)
------------------

- First release on PyPI.
