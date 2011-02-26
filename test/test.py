import socket
import re
import sys
import random
from unittest2 import TestCase, TestSuite, main, TestLoader, skipIf

from bein import *
from bein.util import touch

M = MiniLIMS("testing_lims")


def hostname_contains(pattern):
    hostname = socket.gethostbyaddr(socket.gethostname())[0]
    if re.search(pattern, hostname) == None:
        return False
    else:
        return True

if hostname_contains('vital-it.ch'):
    not_vital_it = False
else:
    not_vital_it = True

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

    @skipIf(not_vital_it, "Not on VITAL-IT.")
    def test_lsf_works(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            q = count_lines._lsf(ex, 'boris')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)            

    def test_nonblocking_with_via_local(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            q = count_lines.nonblocking(ex, 'boris', via='local')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)

    @skipIf(not_vital_it, "Not on VITAL-IT")
    def test_nonblocking_with_via_lsf(self):
        with execution(None) as ex:
            with open('boris','w') as f:
                f.write("This is a test\nof the emergency broadcast\nsystem.\n")
            q = count_lines.nonblocking(ex, 'boris', via='lsf')
            self.assertEqual(str(q.__class__), "<class 'bein.Future'>")
            self.assertEqual(q.wait(), 3)            

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

class TestNoSuchProgramError(TestCase):
    @program
    def nonexistent():
        return {"arguments": ["meepbarf","hilda"],
                "return_value": None}
    
    def test_nonexistent(self):
        with execution(None) as ex:
            self.assertRaises(ValueError, self.nonexistent, ex)

    def test_nonexistent_local(self):
        with execution(None) as ex:
            f = self.nonexistent.nonblocking(ex, via="local")
            self.assertRaises(ValueError, f.wait)

class TestImmutabilityDropped(TestCase):
    def test_immutability_dropped(self):
        executions = []
        with execution(M) as ex:
            touch(ex, "boris")
            ex.add("boris")

        exid1 = ex.id
        borisid = M.search_files(source=('execution',ex.id))[0]
        self.assertFalse(M.fetch_file(borisid)['immutable'])
    
        with execution(M) as ex:
            ex.use(borisid)

        exid2 = ex.id
        self.assertTrue(M.fetch_file(borisid)['immutable'])

        M.delete_execution(exid2)
        self.assertFalse(M.fetch_file(borisid)['immutable'])

        M.delete_execution(exid1)
        self.assertEqual(M.search_files(source=('execution',exid1)), [])

class TestAssociatePreservesFilenames(TestCase):
    def test_associate_with_names(self):
        try:
            with execution(M) as ex:
                touch(ex, "boris")
                touch(ex, "hilda")
                ex.add("boris")
                ex.add("hilda", associate_to_filename="boris", template="%s.meep")
            boris_id = M.search_files(source=('execution',ex.id), with_text="boris")[0]
            hilda_id = M.search_files(source=('execution',ex.id), with_text="hilda")[0]
            boris_name = M.fetch_file(boris_id)['repository_name']
            hilda_name = M.fetch_file(hilda_id)['repository_name']
            self.assertEqual("%s.meep" % boris_name, hilda_name)
        finally:
            try:
                M.delete_execution(ex.id)
            except:
                pass

    def test_associate_with_id(self):
        try:
            fid = M.import_file('test.py')
            with execution(M) as ex:
                touch(ex, "hilda")
                ex.add("hilda", associate_to_id=fid, template="%s.meep")
            hilda_id = M.search_files(source=('execution',ex.id))[0]
            hilda_name = M.fetch_file(hilda_id)['repository_name']
            fid_name = M.fetch_file(fid)['repository_name']
            self.assertEqual("%s.meep" % fid_name, hilda_name)
        finally:
            try:
                M.delete_execution(ex.id)
                M.delete_file(fid)
            except:
                pass

    def test_hierarchical_association(self):
        try:
            with execution(M) as ex:
                touch(ex, "a")
                touch(ex, "b")
                touch(ex, "c")
                ex.add("a")
                ex.add("b", associate_to_filename="a", template="%s.step")
                ex.add("c", associate_to_filename="b", template="%s.step")
            a_id = M.search_files(source=('execution',ex.id), with_text='a')[0]
            b_id = M.search_files(source=('execution',ex.id), with_text='b')[0]
            c_id = M.search_files(source=('execution',ex.id), with_text='c')[0]
            a_name = M.fetch_file(a_id)['repository_name']
            b_name = M.fetch_file(b_id)['repository_name']
            c_name = M.fetch_file(c_id)['repository_name']
            self.assertEqual("%s.step" % a_name, b_name)
            self.assertEqual("%s.step.step" % a_name, c_name)
        finally:
            try:
                M.delete_execution(ex.id)
            except:
                pass

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

