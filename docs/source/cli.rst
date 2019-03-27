Command-line interface
======================

In the simplest form, pygenstub takes a Python source file
as parameter and generates a stub in the same directory::

   $ pygenstub foo.py

.. versionadded:: 1.4.0

   It can also generate stubs for multiple source files::

      $ pygenstub foo.py bar.py baz.py

.. versionadded:: 1.4.0

   If the input is a directory, it will recursively generate
   stubs for all Python source files in the hierarchy::

      $ pygenstub foodir

.. versionadded:: 1.4.0

   By default, stub files will be placed in the same directory
   as their corresponding source files. The ``-o`` option can be
   used to change the directory where the stub files will be stored::

      $ pygenstub foo.py -o out

.. versionadded:: 1.4.0

   By default, pygenstub will ignore any function, method, or variable
   that doesn't have a type signature. If used with the ``--generic``
   option, it will generate output and use the type ``Any`` in such cases::

      $ pygenstub --generic foo.py

.. versionadded:: 1.4.0

   pygenstub can also generate stubs for modules using the ``-m``
   option. In this case, an output directory must be given::

      $ pygenstub -m foo -o out

   Multiple modules are also supported::

      $ pygenstub -m foo -m bar -o out

   When used together with the ``--generic`` option, it can
   generate stub templates for existing modules, even without
   any signatures in the expected format::

      $ pygenstub --generic -m xml -o out

   Note that this is not a main feature for pygenstub;
   the stubgen utility in mypy is probably better suited for this job.
