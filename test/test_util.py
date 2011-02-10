import socket
import re
from unittest import TestCase, TestSuite, main

from bein.util import *

def hostname_contains(pattern):
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    if re.search(pattern, hostname) == None:
        return False
    else:
        return True

class TestBowtie(TestCase):
    def test_parallel_bowtie_local(self):
        with execution(None) as ex:
            bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
                                  '../test_data/reads.raw', n_lines=250,
                                  via='local')
            sam = bam_to_sam(ex, bam)
            new_sam = remove_lines_matching(ex, '@PG', sam)
            new_bam = sam_to_bam(ex, new_sam)
            self.assertEqual(md5sum(ex, new_bam), '2e6bd8ce814949075715b8ffddd1dcd5')

    def test_parallel_bowtie_lsf(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
                                      '../test_data/reads.raw', n_lines=250,
                                      via='lsf')
                sam = bam_to_sam(ex, bam)
                new_sam = remove_lines_matching(ex, '@PG', sam)
                new_bam = sam_to_bam(ex, new_sam)
                self.assertEqual(md5sum(ex, new_bam), '7b7c270a3980492e82591a785d87538f')
        else:
            print >>sys.stderr, "Not running test_parallel_bowtie_lsf because we're not on VITAL-IT"
        



if __name__ == '__main__':
    main()
