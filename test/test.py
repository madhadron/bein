import socket
import re
import sys
import random
from unittest import TestCase, TestSuite, main, TestLoader

from bein import *
from bein.util import touch

M = MiniLIMS("testing_lims")

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
        if m == None:
            return None
        else:
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
            q = count_lines._local(ex, 'boris')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)

    def test_lsf_works(self):
        if hostname_contains('vital-it.ch'):
            with execution(None) as ex:
                with open('boris','w') as f:
                    f.write("This is a test\nof the emergency broadcast\nsystem.\n")
                q = count_lines._lsf(ex, 'boris')
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
            print >>sys.stderr, "Not running test_parallel_bowtie_lsf because we're not on VITAL-IT"


class TestUniqueFilenameIn(TestCase):
    def test_state_determines_filename(self):
        with execution(None) as ex:
            st = random.getstate()
            f = unique_filename_in()
            random.setstate(st)
            g = unique_filename_in()
            self.assertEqual(f, g)

    def test_unique_filename_exact_match(self):
        with execution(None) as ex:
            st = random.getstate()
            f = touch(ex)
            random.setstate(st)
            g = touch(ex)
            self.assertNotEqual(f, g)

    def test_unique_filename_beginnings_match(self):
        with execution(None) as ex:
            st = random.getstate()
            f = unique_filename_in()
            touch(ex, f + 'abcdefg')
            random.setstate(st)
            g = touch(ex)
            self.assertNotEqual(f, g)

class TestMiniLIMS(TestCase):
    def test_resolve_alias_exception_on_no_file(self):
        with execution(None) as ex:
            M = MiniLIMS("boris")
            self.assertRaises(ValueError, M.resolve_alias, 55)

    def test_resolve_alias_returns_int_if_exists(self):
        with execution(None) as ex:
            f = touch(ex)
            M = MiniLIMS("boris")
            a = M.import_file(f)
            self.assertEqual(M.resolve_alias(a), a)

    def test_resolve_alias_with_alias(self):
        with execution(None) as ex:
            f = touch(ex)
            M = MiniLIMS("boris")
            a = M.import_file(f)
            M.add_alias(a, 'hilda')
            self.assertEqual(M.resolve_alias('hilda'), a)

@program
def echo(s):
    return {'arguments': ['echo',str(s)],
            'return_value': None}

class TestStdoutStderrRedirect(TestCase):
    def test_stdout_redirected(self):
        try:
            with execution(M) as ex:
                f = unique_filename_in()
                echo(ex, "boris!", stdout=f)
                with open(f) as q:
                    l = q.readline()
            self.assertEqual(l, 'boris!\n')
        finally:
            M.delete_execution(ex.id)

    def test_stdout_local_redirected(self):
        try:
            with execution(None) as ex:
                f = unique_filename_in()
                m = echo.nonblocking(ex, "boris!", stdout=f)
                m.wait()
                with open(f) as q:
                    l = q.readline()
            self.assertEqual(l, 'boris!\n')
        finally:
            M.delete_execution(ex.id)



def test_given(tests):
    module = sys.modules[__name__]
    if tests == None:
        defaultTest = None
    else:
        loader = TestLoader()
        defaultTest = TestSuite()
        tests = loader.loadTestsFromNames(tests, module)
        defaultTest.addTests(tests)
    main(defaultTest=defaultTest)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_given(sys.argv[1:])
    else:
        test_given(None)

