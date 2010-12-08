``bein.util``
=============

.. automodule:: bein.util

.. function:: bowtie(execution, index, reads, [args="-Sra"])

    Run bowtie with *args* to map *reads* against *index*.

    Returns the filename of bowtie's output file.  *args* gives the
    command line arguments to bowtie, and may be either a string or a
    list of strings.
