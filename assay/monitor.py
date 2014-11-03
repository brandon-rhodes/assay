"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import os
import re
import sys
from pprint import pprint
from time import time
from .discovery import interpret_argument
from .filesystem import Filesystem
from .importation import import_module, improve_order, list_module_paths
from .runner import run_test
from .worker import Worker

def f():
    pass

python3 = (sys.version_info.major >= 3)

def main_loop(names):
    worker = Worker()
    flush = sys.stdout.flush

    results = [interpret_argument(worker, name) for name in names]
    results = [result for result in results if result is not None]
    print(results)

    main_process_paths = set(path for name, path in list_module_paths())
    file_watcher = Filesystem()

    while True:
        # import_order = improve_order(import_order, dangers)
        # print('Importing {}'.format(module_names))
        with worker:
            # t0 = time()
            # module_paths, events = worker(import_modules, import_order)
            # pprint(events)
            # print('  {} seconds'.format(time() - t0))
            # print()
            worker(run_tests_of, names[0])
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

def install_import_path(path):
    sys.modules.insert(0, path)

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
