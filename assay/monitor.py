"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import sys
from pprint import pprint
from time import time
from .assertion import rerun_failing_assert
from .filesystem import wait_on
from .importation import import_module, get_directory_of, improve_order
from .worker import Worker

def f():
    pass

python3 = (sys.version_info.major >= 3)

def main_loop(module_names):
    worker = Worker()
    flush = sys.stdout.flush

    # with worker:
    #     path = worker(get_directory_of, module_name)

    # if path is not None:
    #     raise NotImplementedError('cannot yet introspect full packages')

    # known_modules = set()
    # module_order = []

    # with worker:
    #     paths, events = worker(import_modules, [module_name])

    # # TODO: just return set from worker?

    # for name, names in events:
    #     names = set(names) - known_modules
    #     module_order.extend(names)

    if False:
        # Debugging test of the module orderer: keep running the same
        # set of modules through the partial orderer to see how quickly
        # the order converges on something sensible.
        module_order = list(module_names)
        with worker:
            paths, events = worker(import_modules, module_order)
        pprint(events)
        for i in range(12):
            module_order = improve_order(events)
            with worker:
                paths, events = worker(import_modules, module_order)
            if not i:
                print('--------------------------')
                pprint(events)
        print('--------------------------')
        pprint(events)
        return

    # module_paths = {}

    # with worker:
    #     initial_imports = worker(list_modules)

    # print('Assay up and running with {} modules'.format(len(initial_imports)))

    # import_order = list(module_names)

    while True:
        # import_order = improve_order(import_order, dangers)
        # print('Importing {}'.format(module_names))
        with worker:
            # t0 = time()
            # module_paths, events = worker(import_modules, import_order)
            # pprint(events)
            # print('  {} seconds'.format(time() - t0))
            # print()
            worker(run_tests_of, module_names[0])
            path = worker(path_of, module_names[0])
        print()
        print('Watching', path, end=' ...')
        flush()
        changed_paths = wait_on([path])
        changed_paths
        print()
        print('Running tests')

        # with worker:
        #     before = set(worker(list_modules))
        #     worker(import_modules, [module_name])
        #     after = set(worker(list_modules))
        #     print(after - before)
        #     worker(run_tests_of, module_name)
        # print('Loading dependencies')
        # dependencies = after - before - {module_name}
        # dependencies = [d for d in dependencies if not d.startswith('sky')]
        # print(dependencies)
        # with worker:
        #     worker(import_modules, dependencies)
        #     print('Running tests')
        #     worker(run_tests_of, module_name)

def speculatively_import_then_loop(import_order, ):
    pass


def list_modules():
    return list(sys.modules)

def import_modules(module_names):
    old = set(sys.modules.keys())
    paths = {}
    events = []
    for module_name in module_names:
        try:
            module = import_module(module_name)
        except ImportError:
            continue  # for modules like "pytz.threading"

        path = getattr(module, '__file__', None)
        if path is not None:
            paths[path] = module_name

        new = set(name for name, module in sys.modules.items()
                  if module is not None)
        events.append((module_name, new - old))
        old = new
    return paths, events

def path_of(module_name):
    path = import_module(module_name).__file__
    return path

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
