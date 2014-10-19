
from __future__ import print_function

import inspect
import sys
import traceback
from .assertion import rerun_failing_assert

python3 = (sys.version_info.major >= 3)

def run_test(module, test):
    code = test.__code__ if python3 else test.func_code
    if code.co_argcount:
        parameter_names = inspect.getargs(code).args
        fixtures = [getattr(module, name) for name in parameter_names]
        run_test_with_fixtures(module, test, code, fixtures, ())
    else:
        run_test_with(module, test, code, ())

def run_test_with_fixtures(module, test, code, fixtures, args):
    items = fixtures[0]
    if callable(items):
        items = items()
    if len(fixtures) == 1:
        for item in items:
            run_test_with(module, test, code, args + (item,))
    else:
        remaining_fixtures = fixtures[1:]
        for item in items:
            run_test_with_fixtures(module, test, code,
                                   remaining_fixtures, args + (item,))

def run_test_with(module, test, code, args):
    flush = sys.stderr.flush
    if python3:
        write = sys.stderr.buffer.write
    else:
        write = sys.stderr.write

    try:
        test(*args)
    except AssertionError:
        tb = sys.exc_info()[2]
        message = 'rerun'
        character = b'E'
    except Exception as e:
        tb = sys.exc_info()[2]
        message = '{}: {}'.format(e.__class__.__name__, e)
        character = b'E'
    else:
        message = None
        character = b'.'

    write(character)
    flush()

    if message == 'rerun':
        message = rerun_failing_assert(test, code)

    def black(text): # ';47' does bg color
        return '\033[1;30m' + str(text) + '\033[0m'

    def blue(text):
        return '\033[1;35m' + str(text) + '\033[0m'

    def yellow(text):
        return '\033[1;33m' + str(text) + '\033[0m'

    def red(text):
        return '\033[1;31m' + str(text) + '\033[0m'

    if message is not None:
        frames = traceback.extract_tb(tb)
        frames = frames[1:]
        print()
        for tup in frames:
            filename, line_number, function_name, text = tup
            a = '  {} line {}'.format(filename, line_number)
            b = 'in {}()'.format(function_name)
            f = '{}\n  {}' if (len(a) + len(b) > 78) else '{} {}'
            print(f.format(a, b))
            print('   ', blue(text))
        print(' ', red(message))
        print()
