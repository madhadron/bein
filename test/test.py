import socket
import re
from unittest import TestCase, TestSuite, main

from bein import *

def hostname_contains(pattern):
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    if re.search(pattern, hostname) == None:
        return False
    else:
        return True

@program
def count_lines(filename):
    """Count the number of lines in *filename* (equivalent to ``wc -l``)."""
    def parse_output(p):
        m = re.search(r'^\s*(\d+)\s+' + filename + r'\s*$',
                      ''.join(p.stdout))
        return int(m.groups()[-1]) # in case of a weird line in LSF
    return {"arguments": ["wc","-l",filename],
            "return_value": parse_output}

class TestProgramBinding(TestCase):
    def test_binding_works(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            self.assertEqual(count_lines(ex, 'boris'), 3)

    def test_local_works(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            q = count_lines.local(ex, 'boris')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)

    def test_lsf_works(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                with open('boris','w') as f:
                    f.write("This is a test\nof the emergency broadcast\nsystem.\n")
                q = count_lines.lsf(ex, 'boris')
                self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
                self.assertEqual(q.wait(), 3)            
        else:
            pass

    def test_nonblocking_with_via_local(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            q = count_lines.nonblocking(ex, 'boris', via='local')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)

    def test_nonblocking_with_via_lsf(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                with open('boris','w') as f:
                    f.write("This is a test\nof the emergency broadcast\nsystem.\n")
                q = count_lines.nonblocking(ex, 'boris', via='lsf')
                self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
                self.assertEqual(q.wait(), 3)            
        else:
            pass
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

if __name__ == '__main__':
    main()
