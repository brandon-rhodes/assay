
from __future__ import print_function

import inspect
import linecache
import sys
import traceback
from types import GeneratorType
from .assertion import rerun_failing_assert
from .importation import import_module

class Failure(Exception):
    """Test failure encountered during importation or setup."""

_python3 = (sys.version_info.major >= 3)
_no_such_fixture = object()

def run_tests_of(module_name):
    module = import_module(module_name)
    d = module.__dict__

    test_names = sorted(k for k in d if k.startswith('test_'))
    candidates = [d[k] for k in test_names]
    tests = [t for t in candidates if t.__module__ == module_name]

    for test in tests:
        for result in run_test(module, test):
            yield result

def run_test(module, test):
    args = ()
    code = test.__code__ if _python3 else test.func_code
    if not code.co_argcount:
        yield run_test_with_arguments(module, test, code, args)
        return

    try:
        names = inspect.getargs(code).args
        for args in generate_arguments_from_fixtures(module, names):
            yield run_test_with_arguments(module, test, code, args)
    except Exception as e:
        frames = traceback_frames()
        filename = code.co_filename
        firstlineno = code.co_firstlineno
        if len(frames):
            line = 'Call to fixture {}()'.format(frames[0][2])
        else:
            line = linecache.getline(filename, firstlineno).strip()
        frames.insert(0, (filename, firstlineno, test.__name__, line))
        yield 'F', e.__class__.__name__, str(e), frames

def find_fixture(module, name):
    fixture = getattr(module, name, _no_such_fixture)
    if fixture is _no_such_fixture:
        raise Failure('no such fixture {!r}'.format(name))
    return fixture

def generate_arguments_from_fixtures(module, names):
    fixtures = [find_fixture(module, name) for name in names]
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
    if callable(fixture):
        # try:
        i = fixture()
        # except Exception as e:
        #     raise Failure('fixture {}() raised {}'.format(name, e))
        if not isinstance(i, GeneratorType):
            raise Failure('fixture {}() is not a generator'.format(name))
    else:
        try:
            i = iter(fixture)
        except Exception as e:
            raise Failure('fixture {!r} is not iterable'.format(name))
    return i

def run_test_with_arguments(module, test, code, args):
    try:
        test(*args)
    except AssertionError:
        tb = sys.exc_info()[2]
        frames = traceback.extract_tb(tb)
    except Exception as e:
        tb = sys.exc_info()[2]
        frames = traceback.extract_tb(tb)[1:]
        return 'E', e.__class__.__name__, str(e), add_args(frames, args)
    else:
        return '.'

    message = rerun_failing_assert(test, code, args)
    return 'E', 'AssertionError', message, add_args(frames[-1:], args)

def traceback_frames():
    return [frame for frame in traceback.extract_tb(sys.exc_info()[2])
            if frame[0] != __file__]

def add_args(frames, args):
    filename, lineno, name, line = frames[-1]
    if len(args) == 1:
        name = '{}({!r})'.format(name, args[0])
    elif args:
        name = '{}{!r}'.format(name, args)
    frames[-1] = (filename, lineno, name, line)
    return frames
