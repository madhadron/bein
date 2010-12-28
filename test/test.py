"""
This is a doctest file for bein.util.

parallel_bowtie:

>>> with execution(None) as ex:
...     f = remove_lines_matching(ex, '@PG', '../test_data/mapped.sam')
...     md5sum(ex, f)
'3179a79aef877d2bd0d0cbc184e6d872'

>>> with execution(None) as ex:
...     bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
...                           '../test_data/reads.raw', n_lines=500)
...     sam = bam_to_sam(ex, bam)
...     new_sam = remove_lines_matching(ex, '@PG', sam)
...     new_bam = sam_to_bam(ex, new_sam)
...     md5sum(ex, new_bam)
'7b7c270a3980492e82591a785d87538f'

>>> with execution(None) as ex:
...     md5sum(ex, '../test_data/reads.raw')
'83cfc413a42b4e9086f2a9c33bd943a5'

"""

from bein import *
from bein.util import *
import pysam
import doctest
if __name__ == '__main__':
    doctest.testmod()
