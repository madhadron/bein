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

    def test_parallel_bowtie_local_with_nh_flags(self):
        with execution(None) as ex:
            bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
                                  '../test_data/reads.raw', n_lines=250,
                                  add_nh_flags=True, via='local')
            sam = bam_to_sam(ex, bam)
            new_sam = remove_lines_matching(ex, '@PG', sam)
            new_bam = sam_to_bam(ex, new_sam)
            self.assertEqual(md5sum(ex, new_bam), '529cd218ec0a35d5d0a23fd7b842ee20')

    def test_parallel_bowtie_lsf(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
                                      '../test_data/reads.raw', n_lines=250,
                                      via='lsf')
                sam = bam_to_sam(ex, bam)
                new_sam = remove_lines_matching(ex, '@PG', sam)
                new_bam = sam_to_bam(ex, new_sam)
                self.assertEqual(md5sum(ex, new_bam), 'find right md5sum')

        else:
            print >>sys.stderr, "Not running test_parallel_bowtie_lsf because we're not on VITAL-IT"

    def test_parallel_bowtie_lsf_with_nh_flags(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                bam = parallel_bowtie(ex, '../test_data/selected_transcripts', 
                                      '../test_data/reads.raw', n_lines=250,
                                      add_nh_flags=True, via='lsf')
                sam = bam_to_sam(ex, bam)
                new_sam = remove_lines_matching(ex, '@PG', sam)
                new_bam = sam_to_bam(ex, new_sam)
                self.assertEqual(md5sum(ex, new_bam), '7b7c270a3980492e82591a785d87538f')
        else:
            print >>sys.stderr, "Not running test_parallel_bowtie_lsf because we're not on VITAL-IT"

class TestAddNhFlag(TestCase):
    def test_internal_add_nh_flag(self):
        with execution(None) as ex:
            f = add_nh_flag('../test_data/mapped.sam')
            self.assertEqual(md5sum(ex, f), '50798b19517575533b8ccae5b1369a3e')

    def test_external_add_nh_flag(self):
        with execution(None) as ex:
            f = external_add_nh_flag(ex, '../test_data/mapped.sam')
            g = add_nh_flag('../test_data/mapped.sam')
            self.assertEqual(md5sum(ex, f), md5sum(ex, g))

# 'cat' is used only as an example.  It is useless in Bein.
# class TestCat(TestCase):
#     def test_cat(self):
#         with execution(None) as ex:
#             with open('boris','w') as inp:
#                 inp.write("a\nb\n")
#             f = cat(ex, "boris")
#             n = count_lines(ex, f)
#         self.assertEqual(n, 2)

#     def test_cat_nonblocking(self):
#         with execution(None) as ex:
#             with open('boris','w') as inp:
#                 inp.write("a\nb\n")
#             future = cat.nonblocking(ex, "boris")
#             f = future.wait()
#             n = count_lines(ex, f)
#         self.assertEqual(n, 2)

if __name__ == '__main__':
    main()
