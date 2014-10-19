"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import os
import sys
from pprint import pprint
from time import time
from .filesystem import FileWatcher
from .importation import import_module, get_directory_of, improve_order
from .runner import run_test
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

    main_process_paths = set(path for name, path in list_module_paths())
    file_watcher = FileWatcher()

    # with worker:
    #     events = worker(import_modules, module_names)
    #     module_paths = {path: name for name, path in worker(list_module_paths)}
    #     print(module_paths)
    #     for module_name in module_names:
    #         path = module_paths[module_name]
    #         print(path)

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
            paths = [path for name, path in worker(list_module_paths)]
        print()
        print('Watching', len(paths), 'paths', end='...')
        flush()
        file_watcher.add_paths(paths)
        changes = file_watcher.wait()
        paths = [os.path.join(directory, filename)
                 for directory, filename in changes]
        print(paths)
        main_process_changes = main_process_paths.intersection(paths)
        if main_process_changes:
            example_path = main_process_changes.pop()
            print()
            print('Detected edit to {}'.format(example_path))
            print(' Restart '.center(79, '='))
            restart()
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

def restart():
    executable = sys.executable
    os.execvp(executable, [executable, '-m', 'assay'] + sys.argv[1:])

def speculatively_import_then_loop(import_order, ):
    pass


def list_modules():
    return list(sys.modules)

def import_modules(module_names):
    old = set(name for name, m in sys.modules.items() if m is not None)
    events = []
    for module_name in module_names:
        try:
            import_module(module_name)
        except ImportError:
            continue  # for modules like "pytz.threading"
        new = set(name for name, m in sys.modules.items() if m is not None)
        events.append((module_name, new - old))
        old = new
    return events

def list_module_paths():
    return [(name, module.__file__) for name, module in sys.modules.items()
            if (module is not None) and hasattr(module, '__file__')]

def run_tests_of(module_name):
    module = import_module(module_name)
    d = module.__dict__

    test_names = sorted(k for k in d if k.startswith('test_'))
    candidates = [d[k] for k in test_names]
    tests = [t for t in candidates if t.__module__ == module_name]

    reports = []
    for test in tests:
        run_test(module, test)
    print()
    for report in reports:
        print()
        print(report)
