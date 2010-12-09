.. automodule:: bein.util

  Utilities
  *********

  .. autofunction:: add_figure(execution, figure_type='eps', description="")

  .. autofunction:: add_pickle

  .. autofunction:: count_lines(execution, filename)

  .. autofunction:: pause

  .. autofunction:: sleep(execution, n)

  .. autofunction:: split_file(execution, filename, n_lines = 1000, prefix = None, suffix_length = 3)

  .. autofunction:: touch(execution, filename = None)

  Sequence alignment with ``bowtie``
  **********************************

  .. autofunction:: add_bowtie_index

  .. autofunction:: bowtie(execution, index, reads, [args="-Sra"])

  .. autofunction:: bowtie_build(execution, files, index = None)

  .. autofunction:: parallel_bowtie(execution, index, reads, n_lines = 1000000, bowtie_args = "-Sra", add_nh_flags = False)

  .. autofunction:: parallel_bowtie_lsf(execution, index, reads, n_lines = 1000000, bowtie_args = "-Sra", add_nh_flags = False)

  Manipulating SAM/BAM files
  **************************

  .. autofunction:: add_and_index_bam

  .. autofunction:: add_nh_flag

  .. autofunction:: index_bam(execution, bamfile)

  .. autofunction:: merge_bam(execution, files)

  .. autofunction:: sam_to_bam(execution, sam_filename)

  .. autofunction:: sort_bam(execution, bamfile)

  .. autofunction:: split_by_readname

