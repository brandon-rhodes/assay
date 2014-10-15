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

def main_loop(module_name):
    worker = Worker()

    print('Running sanity check')

    with worker:
        path = worker(get_directory_of, module_name)

    if path is not None:
        raise NotImplementedError('cannot yet introspect full packages')

    while True:
        print('Learning dependencies')
        with worker:
            before = set(worker(list_modules))
            worker(import_modules, [module_name])
            after = set(worker(list_modules))
            print(after - before)
            worker(run_tests_of, module_name)
        print('Loading dependencies')
        dependencies = after - before - {module_name}
        dependencies = [d for d in dependencies if not d.startswith('sky')]
        print(dependencies)
        with worker:
            worker(import_modules, dependencies)
            print('Running tests')
            worker(run_tests_of, module_name)
        break

def list_modules():
    return list(sys.modules)

def import_modules(names):
    for name in names:
        import_module(name)

def run_tests_of(module_name):
    flush = sys.stderr.flush
    if python3:
        write = sys.stderr.buffer.write
    else:
        write = sys.stderr.write

    module = import_module(module_name)
    d = module.__dict__

    good_names = sorted(k for k in d if k.startswith('test_'))
    candidates = [d[k] for k in good_names]
    tests = [t for t in candidates if t.__module__ == module_name]

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
