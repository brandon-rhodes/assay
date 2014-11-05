"""Test suite for Assay.

To run these tests, simply invoke::

    $ python -m assay.tests

"""
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import contextmanager
from . import samples
from .discovery import interpret_argument
from .importation import improve_order
from .runner import run_test

_python3 = (sys.version_info.major >= 3)

# Tests.

class DiscoveryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Note that our directory `b` is inside of an otherwise empty
        # directory in `/tmp`.  Without that level of isolation, someone
        # who put a `__init__.py` in `/tmp` might break these tests.

        cls.temporary_directory = tempfile.mkdtemp(prefix='assaytest')
        cls.base = os.path.join(cls.temporary_directory, 'b')

        def mkdir(*path_components):
            os.mkdir(cls.path(*path_components))

        def touch(*path_components):
            with open(cls.path(*path_components), 'w'):
                pass

        mkdir()
        touch('m1.py')
        touch('m2.py')

        mkdir('p1')
        touch('p1', '__init__.py')
        touch('p1', 'm3.py')
        touch('p1', 'm4.py')
        touch('p1', 'f1.py')

        mkdir('p1', 'p2')
        touch('p1', 'p2', '__init__.py')
        touch('p1', 'p2', 'm5.py')
        touch('p1', 'p2', 'm6.py')

        mkdir('p1', 'd1')
        touch('p1', 'd1', 'm7.py')
        touch('p1', 'd1', 'm8.py')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.temporary_directory)

    @classmethod
    def path(cls, *components):
        return os.path.join(cls.base, *components)

    @contextmanager
    def cd(self, *path_components):
        cwd = os.getcwd()
        os.chdir(self.path(*path_components))
        try:
            yield
        finally:
            os.chdir(cwd)

    def test_file_path_in_current_directory(self):
        with self.cd('p1', 'd1'):
            self.assertEqual(interpret_argument(None, 'm7.py'),
                             ('.', 'm7'))

    def test_file_path_one_directory_deep(self):
        with self.cd('p1'):
            self.assertEqual(interpret_argument(None, 'd1/m7.py'),
                             ('d1', 'm7'))

    def test_file_path_two_directories_deep(self):
        with self.cd():
            self.assertEqual(interpret_argument(None, 'p1/d1/m7.py'),
                             ('p1/d1', 'm7'))

    def test_module_path_in_current_directory(self):
        with self.cd('p1', 'p2'):
            self.assertEqual(interpret_argument(None, 'm5.py'),
                             ('../..', 'p1.p2.m5'))

    def test_module_path_one_package_deep(self):
        with self.cd('p1'):
            self.assertEqual(interpret_argument(None, 'p2/m5.py'),
                             ('..', 'p1.p2.m5'))

    def test_module_path_two_packages_deep(self):
        with self.cd():
            self.assertEqual(interpret_argument(None, 'p1/p2/m5.py'),
                             ('.', 'p1.p2.m5'))

    def test_module_path_two_packages_and_a_directory_deep(self):
        with self.cd('..'):
            self.assertEqual(interpret_argument(None, 'b/p1/p2/m5.py'),
                             ('b', 'p1.p2.m5'))

    def test_package_path_that_is_current_directory(self):
        with self.cd('p1', 'p2'):
            self.assertEqual(interpret_argument(None, '.'),
                             ('../..', 'p1.p2'))

    def test_package_path_that_is_subdirectory(self):
        with self.cd('p1'):
            self.assertEqual(interpret_argument(None, 'p2'),
                             ('..', 'p1.p2'))

    def test_package_path_that_is_subsubdirectory(self):
        with self.cd():
            self.assertEqual(interpret_argument(None, 'p1/p2'),
                             ('.', 'p1.p2'))

    def test_package_path_path_two_packages_and_a_directory_deep(self):
        with self.cd('..'):
            self.assertEqual(interpret_argument(None, 'b/p1/p2'),
                             ('b', 'p1.p2'))


class ErrorMessageTests(unittest.TestCase):

    maxDiff = 10000

    def execute(self, test):
        """Run the test, making strategic line-number adjustments.

        Adjust line numbers to be relative to first line of the test
        function, so that every one of these tests is not broken when an
        additional line gets adding a line to the top of ``samples.py``.

        """
        code = test.__code__ if _python3 else test.func_code
        base = code.co_firstlineno
        result = list(run_test(samples, test))
        for item in result:
            if isinstance(item, tuple):
                trace = item[3]
                for i, frame in enumerate(trace):
                    w, x, y, z = frame
                    trace[i] = w, x - base, y, z
        return result

    def test_passing(self):
        result = self.execute(samples.test_passing)
        self.assertEqual(result, [
            '.',
            ])

    def test_raising_exception(self):
        result = self.execute(samples.test_exc)
        self.assertEqual(result, [
            ('E', 'IOError', 'xyz', [
                ('assay/samples.py', 1, 'test_exc', "raise IOError('xyz')"),
                ]),
            ])

    def test_raising_exception_from_subroutine(self):
        result = self.execute(samples.test_exc2)
        self.assertEqual(result, [
            ('E', 'IOError', 'xyz', [
                ('assay/samples.py', 1, 'test_exc2', "return test_exc()"),
                ('assay/samples.py', -2, 'test_exc', "raise IOError('xyz')"),
                ]),
            ])

    def test_fix0(self):
        result = self.execute(samples.test_fix0)
        self.assertEqual(result, [
            ('F', 'Failure', "no such fixture 'fix0'", [
                ('assay/samples.py', 0, 'test_fix0', 'def test_fix0(fix0):'),
                ]),
            ])

    def test_fix1(self):
        result = self.execute(samples.test_fix1)
        self.assertEqual(result, [
            ('F', 'Failure', "fixture 'fix1' is not iterable", [
                ('assay/samples.py', 0, 'test_fix1', 'def test_fix1(fix1):'),
                ]),
            ])

    def test_fix2(self):
        result = self.execute(samples.test_fix2)
        self.assertEqual(result, [
            '.',
            '.',
            ('E', 'AssertionError', 'it is false that 2 != 2', [
                ('assay/samples.py', 1, 'test_fix2(2)', 'assert fix2 != 2'),
                ]),
            '.',
            ])

    def test_fix3(self):
        result = self.execute(samples.test_fix3)
        self.assertEqual(result, [
            '.',
            ('E', 'AssertionError', 'it is false that 1 != 1', [
                ('assay/samples.py', 1, 'test_fix3(1)', 'assert fix3 != 1'),
                ]),
            ('F', 'ValueError', 'xyz', [
                ('assay/samples.py', 0, 'test_fix3', 'Call to fixture fix3()'),
                ('assay/samples.py', 6, 'fix3', "raise ValueError('xyz')"),
                ]),
            ])

    def test_fix4(self):
        result = self.execute(samples.test_fix4)
        self.assertEqual(result, [
            ('F', 'IOError', 'xyz', [
                ('assay/samples.py', 0, 'test_fix4',
                 'Call to fixture test_exc()'),
                ('assay/samples.py', -27, 'test_exc', "raise IOError('xyz')"),
                ]),
            ])


class ImproveOrderTests(unittest.TestCase):

    # We assume that module B imports A, C imports B, D imports C, et
    # cetera, while modules X and Y and Z are not part of the chain.

    def test_stability_when_nothing_is_wrong(self):
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('D', 'D'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_simple_swap(self):
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('D', 'CD'),
            ('C', ''),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_importing_main_module_first(self):
        events = [
            ('E', 'ABCDE'),
            ('A', ''),
            ('B', ''),
            ('C', ''),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_order_of_imported_modules_is_retained(self):
        events = [
            ('E', 'ABCDE'),
            ('D', ''),
            ('A', ''),
            ('C', ''),
            ('B', ''),
            ]
        self.assertEqual(improve_order(events), ['D', 'A', 'C', 'B', 'E'])

    def test_importing_middle_module_first(self):
        events = [
            ('C', 'ABC'),
            ('A', ''),
            ('B', ''),
            ('D', 'D'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_having_two_module_swaps(self):
        events = [
            ('A', 'A'),
            ('C', 'BC'),
            ('B', ''),
            ('E', 'DE'),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events), ['A', 'B', 'C', 'D', 'E'])

    def test_which_module_moves(self):
        # If module D is moved to the end of the list, then does D
        # simply get moved back, or does E get moved to its right?
        events = [
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('E', 'DE'),
            ('X', 'X'),
            ('Y', 'Y'),
            ('Z', 'Z'),
            ('D', ''),
            ]
        self.assertEqual(improve_order(events),
                         ['A', 'B', 'C', 'X', 'Y', 'Z', 'D', 'E'])

    def test_learning_about_new_modules(self):
        events = [
            ('A', 'A'),
            ('B', 'BX'),
            ('C', 'C'),
            ('D', 'DYZ'),
            ('E', 'E'),
            ]
        self.assertEqual(improve_order(events),
                         ['A', 'X', 'B', 'C', 'Y', 'Z', 'D', 'E'])


if __name__ == '__main__':
    unittest.main()
