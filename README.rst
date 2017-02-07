pygenstub
=========

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


**Classes**

Classes are supported including the imports needed for their base classes.

Code:

.. code-block:: python

   from x import A

   class Foo(A):
       def foo(self, a):
           """Whatever.

           :sig: (int) -> str
           :param a: ...
           """

Stub:

.. code-block:: python

   from x import A

   class Foo(A):
       def foo(self, a: int) -> str: ...


If the docstring of a class has a signature field, it will be used
as the signature field of its ``__init__`` method if that method
doesn't have a signature already.

Code:

.. code-block:: python

   class Foo:
       """Whatever.

       :sig: (int) -> None
       :param a: ...
       """

       def __init__(self, a):
           self.a = a


Stub:

.. code-block:: python

   class Foo:
       def __init__(self, a: int) -> None: ...


**Variables**

Module and class level variables can be annotated using ``# sig:``
comments.

Code:

.. code-block:: python

   x = 42          # sig: int

   class Foo:
       y = 'spam'  # sig: str


Stub:

.. code-block:: python

   x = ...      # type: int

   class Foo:
       y = ...  # type: str


.. note::

   You might think, "why not use ``# type:`` comments directly?".
   That's surely fine but if you do that, you'll need to import the types
   so that the linter or IDE can use them.


TODO
----

- class variables
- decorators
- Sphinx extension for adjusting documentation


Disclaimer
----------

Some of these (or maybe even all of them) are probably
in the "not a good idea" category. The whole thing could be pointless.
I'm experimenting at the moment. Anyway, if you're not using ``.pyi``
files, it should be harmless.
