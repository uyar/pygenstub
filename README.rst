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

At the moment, the utility only handles functions (not methods).
If the docstring for the function includes a **sig** field,
it uses this signature to generate a prototype for the function.

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

Parameter default values will be preserved.

.. code-block:: python

   def foo(a, b=''):
       """Whatever.

       :sig: (int, str) -> None
       :param a: ...
       """

Output:

.. code-block:: python

   def foo(a: int, b: str = '') -> None: ...


**Imported names**

Imported type names in the source will be used in the stub if needed:

.. code-block:: python

   from x import A, B, C

   def foo(a, b):
       """Whatever.

       :sig: (A, B) -> A
       :param a: ...
       """

Output:

.. code-block:: python

   from x import A, B

   def foo(a: A, b: B) -> A: ...


**Dotted names**

Dotted type names will generate imports in the stub file:

.. code-block:: python

   def foo(a, b):
       """Whatever.

       :sig: (x.A, x.B) -> x.A
       :param a: ...
       """

Output:

.. code-block:: python

   import x

   def foo(a: x.A, b: x.B) -> x.A: ...


**Names from the ``typing`` module**

Unresolved names will be looked up from the ``typing`` module:

.. code-block:: python

   def foo(a, b):
       """Whatever.

       :sig: (Dict, Tuple) -> Optional[str]
       :param a: ...
       """

Output:

.. code-block:: python

   from typing import Dict, Optional, Tuple

   def foo(a: Dict, b: Tuple) -> Optional[str]: ...


TODO
----

- Support for methods.
- Sphinx extension for adjusting documentation.


Disclaimer
----------

Some of these (or maybe even all of them) are probably
in the "not a good idea" category. The whole thing could be pointless.
I'm experimenting at the moment. Anyway, if you're not using ``.pyi``
files, it should be harmless.
