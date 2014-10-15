"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import sys
import time
from .assertion import rerun_failing_assert
from .importation import import_module, get_directory_of
from .worker import Worker

def f():
    pass

python3 = (sys.version_info.major >= 3)

def main_loop(name):
    worker = Worker()
    while True:
        print('Learning dependencies')
        with worker:
        # path = worker(get_directory_of, module_name)
        # if path is not None:
        #     raise NotImplementedError('cannot yet introspect full packages')
            t0 = time.time()
            # for i in range(1000):
            before = set(worker(fetch_modules))
            # print((time.time() - t0) / 1000.0)
            t0 = time.time()
            # for i in range(1000):
            #     before = set(worker.list_modules())
            # print((time.time() - t0) / 1000.0)
            #worker.import_modules([name])
            after = set(worker(fetch_modules))
            print(after - before)
            worker(run_tests_of, name)
        break

def fetch_modules():
    return list(sys.modules)

def run_tests_of(name):
    flush = sys.stderr.flush
    if python3:
        write = sys.stderr.buffer.write
    else:
        write = sys.stderr.write

    module = import_module(name)
    d = module.__dict__

    good_names = sorted(k for k in d if k.startswith('test_'))
    candidates = [d[k] for k in good_names]
    tests = [t for t in candidates if t.__module__ == name]

    reports = []
    for t in tests:
        code = t.__code__ if python3 else t.func_code
        if code.co_argcount:
            continue  # TODO: support the idea of fixtures

        try:
            t()
        except AssertionError:
            message = 'rerun'
            character = b'E'
        except Exception as e:
            message = '{}: {}'.format(e.__class__.__name__, e)
            character = b'E'
        else:
            message = None
            character = b'.'

        write(character)
        flush()

        if message == 'rerun':
            message = rerun_failing_assert(t, code)

        if message is not None:
            reports.append('{}:{}\n  {}()\n  {}'.format(
                code.co_filename, code.co_firstlineno, t.__name__, message))
    print()
    for report in reports:
        print()
        print(report)
    return
    for tn in test_names:
        test = d[tn]
        print(test.__module__)
    return []
    names = []
    for name, obj in vars(module).items():
        if not name.startswith('test_'):
            continue
        names.append(name)
    return names
