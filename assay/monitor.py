"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import os
import sys
from time import time
from .discovery import interpret_argument, search_argument
from .filesystem import Filesystem
from .importation import import_module, improve_order, list_module_paths
from .runner import run_tests_of
from .worker import Worker

def f():
    pass

python3 = (sys.version_info.major >= 3)

def main_loop(arguments):
    worker = Worker()
    write = sys.stdout.write
    flush = sys.stdout.flush

    items = [interpret_argument(worker, argument) for argument in arguments]

    main_process_paths = set(path for name, path in list_module_paths())
    file_watcher = Filesystem()

    while True:
        # import_order = improve_order(import_order, dangers)
        # print('Importing {}'.format(module_names))
        t0 = time()
        with worker:
            names = []
            for item in items:
                import_path, import_name = item
                more_names = search_argument(import_path, import_name)
                names.extend(more_names)
            # t0 = time()
            # module_paths, events = worker(import_modules, import_order)
            # pprint(events)
            # print('  {} seconds'.format(time() - t0))
            # print()
            test_count = 0
            for name in names:
                worker.start(run_tests_of, name)
                while True:
                    obj = worker.next()
                    if obj is StopIteration:
                        break
                    elif isinstance(obj, str):
                        write(obj)
                    else:
                        write(repr(obj))
                    test_count += 1
                    flush()
            paths = [path for name, path in worker.call(list_module_paths)]
        print()
        dt = time() - t0
        print('{} tests took {:.2f} seconds'.format(test_count, dt))

        if not sys.stdout.isatty():
            break

        print('Watching', len(paths), 'paths', end='...')
        flush()
        file_watcher.add_paths(paths)
        changes = file_watcher.wait()
        paths = [os.path.join(directory, filename)
                 for directory, filename in changes]

        main_process_changes = main_process_paths.intersection(paths)
        if main_process_changes:
            example_path = main_process_changes.pop()
            print()
            print('Detected edit to {}'.format(example_path))
            print(' Restart '.center(79, '='))
            restart()
        print()
        print('Running tests')

def restart():
    executable = sys.executable
    os.execvp(executable, [executable, '-m', 'assay'] + sys.argv[1:])

def speculatively_import_then_loop(import_order, ):
    pass

def list_modules():
    return list(sys.modules)

def install_import_path(path):
    sys.modules.insert(0, path)
