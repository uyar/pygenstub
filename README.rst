pygenstub is a utility for generating stub files from Python source files.
It takes a source file as input and creates a stub file
with the same base name and the ``.pyi`` extension.

When installed, a script named ``pygenstub`` gets generated which
can be used as follows::

  $ pygenstub foo.py

This command will generate the file ``foo.pyi``.

This utility can be used with the Unix ``watch`` command or PyCharm
file watchers to update stub files automatically from source files.

Features
--------

If the docstring of a function or method includes a **sig** field,
this signature is used to generate a prototype.

For example, considering the code given below:

.. code-block:: python

   def foo(a, b):
       """Whatever.

       :sig: (int, str) -> None
       :param a: ...
       """

The generated prototype will be:

.. code-block:: python

   def foo(a: int, b: str) -> None: ...


**Default values**

The stub will contain placeholders for parameter default values.

Code:

.. code-block:: python

   def foo(a, b=''):
       """Whatever.

       :sig: (int, str) -> None
       :param a: ...
       """

Stub:

.. code-block:: python

   def foo(a: int, b: str = ...) -> None: ...


**Imported names**

Imported type names in the source will be used in the stub *if needed*:

Code:

.. code-block:: python

   from x import A, B, C

   def foo(a, b):
       """Whatever.

       :sig: (A, B) -> A
       :param a: ...
       """

Stub (note that the name ``C`` is not imported):

.. code-block:: python

   from x import A, B

   def foo(a: A, b: B) -> A: ...


**Dotted names**

Dotted type names will generate imports in the stub file.

Code:

.. code-block:: python

   def foo(a, b):
       """Whatever.

       :sig: (x.y.A, x.y.B) -> x.y.A
       :param a: ...
       """

Stub:

.. code-block:: python

   import x.y

   def foo(a: x.y.A, b: x.y.B) -> x.y.A: ...


**Names from the typing module**

Unresolved names will be looked up from the ``typing`` module.

Code:

.. code-block:: python

   def foo(a, b):
       """Whatever.

       :sig: (Dict, Tuple) -> Optional[str]
       :param a: ...
       """

Stub:

.. code-block:: python

   from typing import Dict, Optional, Tuple

   def foo(a: Dict, b: Tuple) -> Optional[str]: ...


TODO
----

- Support for instance/class variables.
- Support for annotations.
- Sphinx extension for adjusting documentation.


Disclaimer
----------

Some of these (or maybe even all of them) are probably
in the "not a good idea" category. The whole thing could be pointless.
I'm experimenting at the moment. Anyway, if you're not using ``.pyi``
files, it should be harmless.
