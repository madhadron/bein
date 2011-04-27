import os
from unittest2 import TestCase, TestSuite, main, TestLoader

from bein import *
from bein.util import touch

M = MiniLIMS("testing_lims")

@task
def path_is(ex):
    """Documentation!"""
    return os.getcwd()

@task
def add_file(ex):
    touch(ex, "boris")
    ex.add("boris", description="test")

class TestTask(TestCase):

    def test_is_in_subdir(self):
        q = path_is(None)
        self.assertEqual(os.path.split(q['value'])[0],
                         os.getcwd())

    def test_no_description(self):
        q = path_is(M)
        self.assertEqual(M.fetch_execution(q['execution'])['description'], '')

    def test_with_description(self):
        d = "This is a test"
        q = path_is(M, description=d)
        self.assertEqual(M.fetch_execution(q['execution'])['description'], d)

    def test_returns_files(self):
        q = add_file(M)
        file_id = q['files']['test']
        self.assertEqual(M.fetch_file(file_id)['external_name'], 'boris')

    def test_docstring_correct(self):
        self.assertEqual(path_is.__doc__, "Documentation!")

    def test_name_correct(self):
        self.assertEqual(path_is.__name__, "path_is")

if __name__ == '__main__':
    main()

