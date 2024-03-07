"""Test suite for Assay.

To run these tests, simply invoke::

    $ python -m assay.tests

"""
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from . import samples
from .compatibility import get_code, unittest
from .discovery import interpret_argument
from .importation import improve_order, list_module_paths
from .runner import run_tests_of, run_test
from .samples import mul
from .worker import Worker

_python3 = sys.version_info >= (3,)
_python33 = sys.version_info >= (3, 3)
_python38 = sys.version_info >= (3, 8)

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

    def test_pep420_namespace_package_is_omitted_from_module_paths(self):
        if not _python33:
            return
        with self.cd('p1'):
            os.unlink('__init__.py')
        sys.path.append(self.path())
        __import__('p1.p2')
        d = dict(list_module_paths())
        assert 'p1' not in d
        assert d['p1.p2'] == self.path('p1', 'p2', '__init__.py')


class RunnerTests(unittest.TestCase):

    maxDiff = 9999

    def test_runner_on_good_module(self):
        value = list(run_tests_of('assay.samples'))
        self.assertEqual(len(value), 35)

    def test_runner_on_syntax_error(self):
        with tempfile.NamedTemporaryFile(suffix='.py') as f:
            f.write(b'\n\nif while\n')
            f.flush()
            basename = os.path.basename(f.name)
            module_name = basename[:-3]
            sys.path.insert(0, os.path.dirname(f.name))
            if _python33:
                import importlib
                importlib.invalidate_caches()
            try:
                value = list(run_tests_of(module_name))
            finally:
                del sys.path[0]
        arrow = '   ^' if _python38 else '       ^'
        self.assertEqual(value, [
            ('F', 'SyntaxError',
             'invalid syntax ({0}, line 3)'.format(basename),
             [(f.name, 3, None, 'if while\n' + arrow)]),
            ])

    def test_runner_on_module_that_throws_exception_during_import(self):
        with tempfile.NamedTemporaryFile(suffix='.py') as f1:
          with tempfile.NamedTemporaryFile(suffix='.py') as f2:
            module_name1 = os.path.basename(f1.name)[:-3]
            module_name2 = os.path.basename(f2.name)[:-3]
            f1.write(b'\n\n\nimport ' + module_name2.encode('ascii') + b'\n')
            f1.flush()
            f2.write(b'\ndict()["key"]\n')
            f2.flush()
            sys.path.insert(0, os.path.dirname(f1.name))
            if _python33:
                import importlib
                importlib.invalidate_caches()
            try:
                value = list(run_tests_of(module_name1))
            finally:
                del sys.path[0]
        self.assertEqual(value, [
            ('F', 'KeyError', "'key'",
             [(f1.name, 4, '<module>', 'import {0}'.format(module_name2)),
              (f2.name, 2, '<module>', 'dict()["key"]')]),
            ])


class ErrorMessageTests(unittest.TestCase):

    maxDiff = 10000

    def execute(self, test):
        """Run the test, making strategic line-number adjustments.

        Adjust line numbers to be relative to first line of the test
        function, so that every one of these tests is not broken when an
        additional line gets adding a line to the top of ``samples.py``.

        """
        code = get_code(test)
        base = code.co_firstlineno
        result = list(run_test(samples, test))
        for item in result:
            if isinstance(item, tuple):
                frames = item[3]
                for i in range(len(frames)):
                    filename, lineno, name, line = frames[i]
                    if filename.rstrip('c').endswith('/samples.py'):
                        frames[i] = filename, lineno - base, name, line
        return result

    def test_passing(self):
        result = self.execute(samples.test_passing)
        self.assertEqual(result, [
            '.',
            ])

    def test_plain_assertion(self):
        result = self.execute(samples.test_assert0)
        self.assertEqual(result, [
            ('E', 'AssertionError', '', [
                ('assay/samples.py', 1, 'test_assert0', 'assert False')
                ]),
            ])

    def test_equality_assertion(self):
        result = self.execute(samples.test_assert1)
        self.assertEqual(result, [
            ('E', 'AssertionError', '2 != 4', [
                ('assay/samples.py', 1, 'test_assert1', 'assert 1+1 == 2+2')
                ]),
            ])

    def test_equality_assertion_in_subroutine(self):
        result = self.execute(samples.test_assert2)
        self.assertEqual(result, [
            ('E', 'AssertionError', '4 != 6', [
                ('assay/samples.py', 1, 'test_assert2', 'sub_assert2()'),
                ('assay/samples.py', -2, 'sub_assert2', 'assert 2+2 == 3+3')
                ]),
            ])

    def test_assertion_in_long_function_that_uses_EXTENDED_ARG(self):
        result = self.execute(samples.test_assert3)
        self.assertEqual(result, [
            ('E', 'AssertionError', '270 != 100', [
                ('assay/samples.py', 4, 'test_assert3', 'assert n == 100'),
                ]),
            ])

    def test_assert_with_tab(self):
        result = self.execute(samples.test_assert_tab)
        self.assertEqual(result, [
            ('E', 'AssertionError', '2 != 3', [
                ('assay/samples.py', 1, 'test_assert_tab', 'assert\t1+1 == 3')
                ]),
            ])

    def test_assert_that_raises_no_exception_the_second_time(self):
        result = self.execute(samples.test_assert_then_pass)
        self.assertEqual(result, [
            ('E', 'AssertionError', 'Assay re-ran your test to examine its'
             ' failed assert, but it passed the second time', [
                ('assay/samples.py', 3, 'test_assert_then_pass',
                 'assert 1+1 == 3')
                ]),
            ])

    def test_assert_that_raises_a_different_exception_the_second_time(self):
        result = self.execute(samples.test_assert_then_die)
        self.assertEqual(result, [
            ('E', 'AssertionError', 'Assay re-ran your test to examine its'
             ' failed assert, but the second time it raised'
             ' ValueError: bad value', [
                ('assay/samples.py', 3, 'test_assert_then_die',
                 'assert 1+1 == 3')
                ]),
            ])

    def test_raising_exception(self):
        result = self.execute(samples.test_exc)
        self.assertEqual(result, [
            ('E', 'OSError', 'xyz', [
                ('assay/samples.py', 1, 'test_exc', "raise OSError('xyz')"),
                ]),
            ])

    def test_raising_exception_from_subroutine(self):
        result = self.execute(samples.test_exc2)
        self.assertEqual(result, [
            ('E', 'OSError', 'xyz', [
                ('assay/samples.py', 1, 'test_exc2', "return test_exc()"),
                ('assay/samples.py', -2, 'test_exc', "raise OSError('xyz')"),
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
            ('E', 'AssertionError', '2 == 2', [
                ('assay/samples.py', 1, 'test_fix2(2)', 'assert fix2 != 2'),
                ]),
            '.',
            ])

    def test_fix3(self):
        result = self.execute(samples.test_fix3)
        self.assertEqual(result, [
            '.',
            ('E', 'AssertionError', '1 == 1', [
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
            ('F', 'OSError', 'xyz', [
                ('assay/samples.py', 0, 'test_fix4',
                 'Call to fixture test_exc()'),
                ('assay/samples.py', -27, 'test_exc', "raise OSError('xyz')"),
                ]),
            ])

    def test_syntax_error(self):
        result = self.execute(samples.test_syntax_error)
        self.assertEqual(result, [
            ('E', 'SyntaxError', 'invalid syntax (<string>, line 1)', [
                ('assay/samples.py', 1, 'test_syntax_error', "eval('1+2!3')"),
                ('<string>', 1, None, '1+2!3\n   ^'),
                ]),
            ])

    def test_raises_with_correct_exception(self):
        result = self.execute(samples.test_raises1)
        self.assertEqual(result, [
            '.',
            ])

    def test_raises_with_correct_exception_and_message(self):
        result = self.execute(samples.test_raises2)
        self.assertEqual(result, [
            '.',
            ])

    def test_raises_with_wrong_exception(self):
        result = self.execute(samples.test_raises3)
        self.assertEqual(result, [
            ('E', 'KeyError', "'correct message but wrong exception'", [
                ('assay/samples.py', 2, 'test_raises3',
                 "raise KeyError('correct message but wrong exception')"),
                ]),
            ])

    def test_raises_with_wrong_message(self):
        result = self.execute(samples.test_raises4)
        self.assertEqual(result, [
            ('E', 'AssertRaisesError',
             "cannot find pattern 'one message' in 'another message'", [
                 ('assay/samples.py', 2, 'test_raises4',
                  "raise ValueError('another message')"),
                 ]),
            ])

    # The following tests verify that we intercept and correctly report
    # failed results for all basic asserts in `opcode.cmp_op`:
    # ('<', '<=', '==', '!=', '>', '>=')

    def test_assert_lt(self):
        result = self.execute(samples.test_lt)
        self.assertEqual(result, [
            ('E', 'AssertionError', '7 not less than 3', [
                ('assay/samples.py', 1, 'test_lt', 'assert 3+4 < 1+2')
            ]),
        ])

    def test_assert_le(self):
        result = self.execute(samples.test_le)
        self.assertEqual(result, [
            ('E', 'AssertionError', '7 not less than or equal to 3', [
                ('assay/samples.py', 1, 'test_le', 'assert 3+4 <= 1+2')
            ]),
        ])

    def test_assert_eq(self):
        result = self.execute(samples.test_eq)
        self.assertEqual(result, [
            ('E', 'AssertionError', '3 != 7', [
                ('assay/samples.py', 1, 'test_eq', 'assert 1+2 == 3+4')
            ]),
        ])

    def test_assert_ne(self):
        result = self.execute(samples.test_ne)
        self.assertEqual(result, [
            ('E', 'AssertionError', '3 == 3', [
                ('assay/samples.py', 1, 'test_ne', 'assert 1+2 != 0+3')
            ]),
        ])

    def test_assert_gt(self):
        result = self.execute(samples.test_gt)
        self.assertEqual(result, [
            ('E', 'AssertionError', '3 not greater than 7', [
                ('assay/samples.py', 1, 'test_gt', 'assert 1+2 > 3+4')
            ]),
        ])

    def test_assert_ge(self):
        result = self.execute(samples.test_ge)
        self.assertEqual(result, [
            ('E', 'AssertionError', '3 not greater than or equal to 7', [
                ('assay/samples.py', 1, 'test_ge', 'assert 1+2 >= 3+4')
            ]),
        ])

    def test_assert_in(self):
        result = self.execute(samples.test_in)
        self.assertEqual(result, [
            ('E', 'AssertionError', '1 not found in ()', [
                ('assay/samples.py', 1, 'test_in', 'assert 1 in ()')
            ]),
        ])

    def test_assert_not_in(self):
        result = self.execute(samples.test_not_in)
        self.assertEqual(result, [
            ('E', 'AssertionError', '1 unexpectedly found in (1,)', [
                ('assay/samples.py', 1, 'test_not_in', 'assert 1 not in (1,)')
            ]),
        ])

    def test_assert_is(self):
        result = self.execute(samples.test_is)
        self.assertEqual(result, [
            ('E', 'AssertionError', 'None is not 1', [
                ('assay/samples.py', 2, 'test_is', 'assert None is n')
            ]),
        ])

    def test_assert_is_not(self):
        result = self.execute(samples.test_is_not)
        self.assertEqual(result, [
            ('E', 'AssertionError', 'unexpectedly identical: None', [
                ('assay/samples.py', 1, 'test_is_not',
                 'assert None is not None')
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

PRETEND_PIPE_LIMIT = 256

class BlockReader(object):
    """Challenge: can we survive a pipe that splits long data into blocks?"""
    def __init__(self, file):
        self.file = file
        self.close = file.close

    def read(self, n=-1):
        n = min(n, PRETEND_PIPE_LIMIT)
        return self.file.read(n)

    def readline(self, n=-1):
        raise NotImplementedError()

class WorkerTests(unittest.TestCase):
    def test_worker_can_call_simple_function(self):
        w = Worker()
        try:
            answer = w.call(mul, 3, 4)
            self.assertEqual(answer, 12)
        finally:
            w.close()

    def test_worker_survive_narrow_pipe(self):
        # This simulates a difficult-to-reproduce problem: until we
        # enhanced the Worker, on Python 3 on GitHub Actions the main
        # process would sometimes raise "_pickle.UnpicklingError: pickle
        # data was truncated".
        if not _python3:
            return
        n = 5 * PRETEND_PIPE_LIMIT
        w = Worker()
        w.from_worker = BlockReader(w.from_worker)
        try:
            answer = w.call(mul, 'a', n)
        finally:
            w.close()
        self.assertEqual(answer, 'a' * n)

if __name__ == '__main__':
    unittest.main()
