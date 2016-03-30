"""Routines for finding a test's fixtures (if any) and running the test."""

from __future__ import print_function

import assay
import inspect
import linecache
import os
import sys
from types import FunctionType
from .assertion import get_code, search_for_function, rewrite_asserts_in
from .importation import import_module

class Failure(Exception):
    """Test failure encountered during importation or setup."""

_python3 = sys.version_info >= (3,)
_no_such_fixture = object()
_is_noisy_filename = (__file__, assay.__file__).__contains__

if _python3:
    from io import StringIO
else:
    from StringIO import StringIO

def capture_stdout_stderr(generator, *args):
    """Call a generator, supplementing its tuples with stdout, stderr data."""
    oldout = sys.stdout
    olderr = sys.stderr
    out = StringIO()
    err = StringIO()
    sys.stdout = out
    sys.stderr = err
    try:
        for item in generator(*args):
            if isinstance(item, tuple):
                yield item + (out.getvalue(), err.getvalue())
            else:
                yield item
            out.truncate(0)
            err.truncate(0)
    finally:
        sys.stdout = oldout
        sys.stderr = olderr

def run_tests_of(module_name):
    """Run all tests discovered inside of a module."""
    try:
        module = import_module(module_name)
    except Exception as e:
        frames = [frame for frame in traceback_frames()
                  if ('/importlib/' not in frame[0])
                  and (' importlib.' not in frame[0])]
        yield 'F', e.__class__.__name__, str(e), frames
        return

    tests = sorted((k, v) for k, v in module.__dict__.items()
                   if k.startswith('test_') and isinstance(v, FunctionType)
                   and getattr(v, '__module__', '') == module_name)

    for name, test in tests:
        for result in run_test(module, test):
            yield result

def run_test(module, test):
    """Run a test, detecting whether it needs fixtures and providing them."""
    code = get_code(test)
    if not code.co_argcount:
        yield run_test_with_arguments(test, ())
        return

    try:
        names = inspect.getargs(code).args
        fixtures = [find_fixture(module, name) for name in names]
        for args in generate_arguments_from_fixtures(names, fixtures):
            yield run_test_with_arguments(test, args)
    except Exception as e:
        frames = traceback_frames()
        filename = relativize(code.co_filename)
        firstlineno = code.co_firstlineno
        if len(frames):
            # TODO: what if the fixture called a subroutine?
            line = 'Call to fixture {0}()'.format(frames[0][2])
        else:
            line = linecache.getline(filename, firstlineno).strip()
        frames.insert(0, (filename, firstlineno, test.__name__, line))
        yield 'F', e.__class__.__name__, str(e), frames

def find_fixture(module, name):
    """Try to resolve a fixture, given its name and the test module."""
    fixture = getattr(module, name, _no_such_fixture)
    if fixture is _no_such_fixture:
        raise Failure('no such fixture {0!r}'.format(name))
    return fixture

def generate_arguments_from_fixtures(names, fixtures):
    """Yield all combinations of the outputs of a list of fixtures.

    >>> list(generate_arguments_from_fixtures(['f1', 'f2'], ['AB', 'xy']))
    [('A', 'x'), ('A', 'y'), ('B', 'x'), ('B', 'y')]

    """
    iterators = [iterate_over_fixture(name, fixture) for name, fixture
                 in zip(names, fixtures)]
    args = [next(i) for i in iterators]
    backwards = list(reversed(range(len(iterators))))
    while True:
        yield tuple(args)
        for j in backwards:
            try:
                args[j] = next(iterators[j])
            except StopIteration:
                iterators[j] = iterate_over_fixture(names[j], fixtures[j])
                args[j] = next(iterators[j])
            else:
                break
        else:
            return

def iterate_over_fixture(name, fixture):
    """Try iterating over a fixture, whether it is a sequence or generator."""
    if callable(fixture):
        fixture = fixture()  # TODO: make fixtures able to take other fixtures
    try:
        return iter(fixture)
    except Exception:
        raise Failure('fixture {0!r} is not iterable'.format(name))

def run_test_with_arguments(test, args):
    """Return the result of invoking a test with the given arguments."""
    try:
        test(*args)
    except AssertionError as e:
        type_name = type(e).__name__
        message = str(e)
        frames, frame = traceback_frames(return_top_frame=True)
        filename, lineno, name, text = frames[-1]
        function = search_for_function(frame.f_code, test, frame, name)
        del frame
    except Exception as e:
        frames = traceback_frames()
        return 'E', type(e).__name__, str(e), add_args(frames, args)
    else:
        return '.'

    if not message:
        if text.startswith('assert') and not text[6].isalnum():
            if function and not hasattr(function, 'assay_rewritten'):
                rewrite_asserts_in(function)
                function.assay_rewritten = True
                try:
                    test(*args)
                except AssertionError as e:
                    message = str(e)
                except Exception as e:
                    type_name2, message2 = type(e).__name__, str(e)
                    message = ('Assay re-ran your test to examine its failed assert, but the'
                               ' second time it raised {0}: {1}'.format(type_name2, message2))
                else:
                    message = ('Assay re-ran your test to examine its failed assert, but it'
                               ' passed the second time')

            if not message:
                pass  # TODO: slower introspection

    return 'E', type_name, message, add_args(frames, args)

def traceback_frames(return_top_frame=False):
    """Return traceback frames for code outside of this file.

    The result is a list of tuples in the usual style of extract_tb(tb),
    except that a bonus tuple is added in the case of a SyntaxError.  If
    `return_top_frame` is true, a frame object is also returned.

    """
    etype, e, tb = sys.exc_info()
    tuples = []
    while tb is not None:
        frame = tb.tb_frame
        code = frame.f_code
        filename = code.co_filename
        if not _is_noisy_filename(filename):
            lineno = frame.f_lineno
            line = linecache.getline(filename, lineno, frame.f_globals)
            line = line.strip() if line else None
            tuples.append((relativize(filename), lineno, code.co_name, line))
        tb = tb.tb_next
    if isinstance(e, SyntaxError) and (e.text is not None):
        line = '{0}\n{1}^'.format(e.text.rstrip(), ' ' * (e.offset - 1))
        tuples.append((relativize(e.filename), e.lineno, None, line))
    return (tuples, frame) if return_top_frame else tuples

def relativize(path):
    """Turn a path into a relative path if it lives beneath our directory."""
    relative = os.path.relpath(path)
    return path if relative.startswith('..') else relative

def add_args(frames, args):
    """Rewrite traceback to show the test function's arguments."""
    if args:
        path, lineno, name, line = frames[-1]
        argstr = repr(args)[1:-1].rstrip(',')
        name = '{0}({1})'.format(name, argstr)
        frames[-1] = (path, lineno, name, line)
    return frames
