.. automodule:: bein

  Executions
  ***********

  .. autofunction:: execution

  .. autoclass:: Execution

    .. automethod:: add

    .. automethod:: use

  MiniLIMS
  *********

  .. autoclass:: MiniLIMS

    .. automethod:: add_alias

    .. automethod:: associate_file

    .. automethod:: associated_files_of

    .. automethod:: copy_file

    .. automethod:: delete_alias

    .. automethod:: delete_execution

    .. automethod:: delete_file

    .. automethod:: delete_file_association

    .. automethod:: export_file

    .. automethod:: fetch_execution

    .. automethod:: fetch_file

    .. automethod:: import_file

    .. automethod:: path_to_file

    .. automethod:: resolve_alias

    .. automethod:: search_executions

    .. automethod:: search_files

  Programs
  *********

  .. autoclass:: program

  Miscellaneous
  **************

  .. autofunction:: unique_filename_in

  .. autoclass:: bein.ProgramOutput

    .. attribute:: return_code

      An integer giving the return code of the program when it exited.
      By convention this is 0 if the program succeeded, or some other
      value if it failed.

    .. attribute:: pid

      An integer giving the process ID under which the program ran.

    .. attribute:: arguments

      A list of strings which were the program and the exact arguments
      passed to it.

    .. attribute:: stdout

      The text printed by the program to ``stdout``.  It is returned
      as a list of strings, each corresponding to one line of
      ``stdout``, and each still carrying their terminal ``\n``.

    .. attribute:: stderr

      The text printed by the program to ``stderr``.  It has the same
      format as ``stdout``.


  .. autoexception:: ProgramFailed
