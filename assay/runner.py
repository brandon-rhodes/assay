
from __future__ import print_function

import inspect
import sys
import traceback
from .assertion import rerun_failing_assert

python3 = (sys.version_info.major >= 3)

def run_test(test):
    flush = sys.stderr.flush
    if python3:
        write = sys.stderr.buffer.write
    else:
        write = sys.stderr.write

    code = test.__code__ if python3 else test.func_code
    if code.co_argcount:
        parameter_names = inspect.getargs(code).args
        print(parameter_names)

    try:
        test()
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
        for tup in traceback.extract_tb(tb):
            filename, line_number, function_name, text = tup
            a = '  {} line {}'.format(filename, line_number)
            b = 'in {}()'.format(function_name)
            f = '{}\n  {}' if (len(a) + len(b) > 78) else '{} {}'
            print(f.format(a, b))
            print('   ', blue(text))
            # print('  {} line {} in {}\n    {}'.format(
            #     , , text))
        print(' ', red(message))
        # reports.append('{}:{}\n  {}()\n  {}'.format(
        #     code.co_filename, code.co_firstlineno, t.__name__))
        print()
