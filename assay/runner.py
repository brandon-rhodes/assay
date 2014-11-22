"""Routines for finding a test's fixtures (if any) and running the test."""

from __future__ import print_function

import inspect
import linecache
import os
import sys
import traceback
from types import FunctionType
from .assertion import rewrite_asserts_in
from .importation import import_module

class Failure(Exception):
    """Test failure encountered during importation or setup."""

_python3 = (sys.version_info.major >= 3)
_no_such_fixture = object()

if _python3:
    from io import StringIO
else:
    from StringIO import StringIO

def _get_code(function):
    return function.__code__ if _python3 else function.func_code

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
    code = _get_code(test)
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
            line = 'Call to fixture {}()'.format(frames[0][2])
        else:
            line = linecache.getline(filename, firstlineno).strip()
        frames.insert(0, (filename, firstlineno, test.__name__, line))
        yield 'F', e.__class__.__name__, str(e), frames

def find_fixture(module, name):
    """Try to resolve a fixture, given its name and the test module."""
    fixture = getattr(module, name, _no_such_fixture)
    if fixture is _no_such_fixture:
        raise Failure('no such fixture {!r}'.format(name))
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
        raise Failure('fixture {!r} is not iterable'.format(name))

def run_test_with_arguments(test, args):
    """Return the result of invoking a test with the given arguments."""
    try:
        test(*args)
    except AssertionError as e:
        type_name = type(e).__name__
        message = str(e)
        frames = traceback_frames()
        filename, lineno, name, text = frames[-1]
        tb = sys.exc_info()[2]
        while tb.tb_next:
            tb = tb.tb_next
        tb_frame = tb.tb_frame
        failed_code = tb_frame.f_code
        test_code = _get_code(test)
        if failed_code is test_code:
            function = test
        else:
            maybe_function = (tb_frame.f_locals.get(name) or
                              tb_frame.f_globals.get(name))
            if (isinstance(maybe_function, FunctionType)
                  and _get_code(maybe_function) is failed_code):
                function = maybe_function
            else:
                function = None
        del tb
        del tb_frame
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
                               ' second time it raised {}: {}'.format(type_name2, message2))
                else:
                    message = ('Assay re-ran your test to examine its failed assert, but it'
                               ' passed the second time')

            if not message:
                pass  # TODO: slower introspection

    return 'E', type_name, message, add_args(frames, args)

def traceback_frames():
    """Return all traceback frames for code outside of this file."""
    etype, e, tb = sys.exc_info()
    frames = [(relativize(filename), lineno, name, line)
              for filename, lineno, name, line in traceback.extract_tb(tb)
              if filename != __file__]
    if isinstance(e, SyntaxError):
        line = '{}\n{}^'.format(e.text.rstrip(), ' ' * (e.offset - 1))
        frames.append((relativize(e.filename), e.lineno, None, line))
    return frames

def relativize(path):
    """Turn a path into a relative path if it lives beneath our directory."""
    relative = os.path.relpath(path)
    return path if relative.startswith('..') else relative

def add_args(frames, args):
    """Rewrite traceback to show the test function's arguments."""
    if args:
        path, lineno, name, line = frames[-1]
        argstr = repr(args)[1:-1].rstrip(',')
        name = '{}({})'.format(name, argstr)
        frames[-1] = (path, lineno, name, line)
    return frames
