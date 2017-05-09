Features
========

This document describes how pygenstub generates the stub files from the source.

Methods
-------

Methods are handled the same way as functions except that there is no type hint
for the ``self`` parameter (assuming it's the first parameter):

:code:

   .. code-block:: python

      class Foo:
          def foo(self, a):
              """Do foo.

              :sig: (int) -> None
              """

:stub:

   .. code-block:: python

      class Foo:
          def foo(self, a: int) -> None: ...

Imported names
--------------

Imported type names in the source will be used in the stub file *if needed*:

:code:

   .. code-block:: python

      from x import A, B, C

      def foo(a, b):
          """Do foo.

          :sig: (A, B) -> A
          """

:stub:

   .. code-block:: python

      from x import A, B

      def foo(a: A, b: B) -> A: ...

Note that the name ``C`` is not imported in the stub file.

Qualified names
---------------

Qualified (dotted) type names will generate import lines in the stub file
if they are not already imported:

:code:

   .. code-block:: python

      from z import x

      def foo(a, b):
          """Do foo.

          :sig: (x.A, y.B) -> m.n.C
          """

:stub:

   .. code-block:: python

      from z import x
      import y
      import m.n

      def foo(a: x.A, b: y.B) -> m.n.C: ...

Names from the ``typing`` module
--------------------------------

Unresolved names will be looked up in the ``typing`` module.

:code:

   .. code-block:: python

      def foo(a, b):
          """Do foo.

          :sig: (List[int], Mapping[str, int]) -> Iterable[str]
          """

:stub:

   .. code-block:: python

      from typing import Iterable, List, Mapping

      def foo(a: List[int], b: Mapping[str, int]) -> Iterable[str]: ...

Default values
--------------

If a parameter has a default value, the prototype will contain the triple dots
placeholder for it:

:code:

   .. code-block:: python

      def foo(a, b=''):
          """Do foo.

          :sig: (int, Optional[str]) -> None
          """

:stub:

   .. code-block:: python

      from typing import Optional

      def foo(a: int, b: Optional[str] = ...) -> None: ...

Base classes
------------

The imports needed for base classes will be included or generated using
the same rules as described above (imported, dotted, etc.):

:code:

   .. code-block:: python

      from x import A

      class Foo(A, y.B):
          def foo(self, a):
              """Do foo.

              :sig: (int) -> None
              """

:stub:

   .. code-block:: python

      from x import A
      import y

      class Foo(A, y.B):
          def foo(self, a: int) -> None: ...

Class signatures
----------------

If the docstring of a class has a signature field, it will be used as
the signature field of its ``__init__`` method unless that method already
has a signature.

:code:

   .. code-block:: python

      class Foo:
          """A foo.

          :sig: (int) -> None
          """

          def __init__(self, a):
              self.a = a

:stub:

   .. code-block:: python

      class Foo:
          def __init__(self, a: int) -> None: ...

Signature comments
------------------

Type hints for assignments can be written using ``# sig:`` comments.

:code:

   .. code-block:: python

      n = 42  # sig: int


:stub:

   .. code-block:: python

      n = ...  # type: int

The rules for importing names as described above also apply here.

.. note::

   The reason for using ``# sig`` comment instead of a ``# type`` comment
   would be to avoid having to import the types.

Instance variables
------------------

Within classes, assignments to attributes of ``self`` will generate
assignments with type comments under the class:

:code:

   .. code-block:: python

      class Foo:
          def foo(self):
              self.y = 'spam'  # sig: str

:stub:

   .. code-block:: python

      class Foo:
          y = ...  # type: str

Long lines
----------

If the prototype line gets too long, it will be divided into multiple lines:

:code:

   .. code-block:: python

      def some_long_func_name(some_long_param_name_1, some_long_param_name_2):
          """Do foo.

          :sig: (some_long_type_1, some_long_type_2) -> some_long_type_3
          """

:stub:

   .. code-block:: python

      def some_long_func_name(
              some_long_param_name_1: some_long_type_1,
              some_long_param_name_2: some_long_type_2
      ) -> some_long_type_3: ...
