"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import contextlib
import os
import select
import sys
from time import time
from .discovery import interpret_argument, search_argument
from .filesystem import Filesystem
from .importation import import_module, improve_order, list_module_paths
from .runner import capture_stdout_stderr, run_tests_of
from .worker import Worker

def f():
    pass

python3 = (sys.version_info.major >= 3)

def main_loop(arguments, is_interactive):
    worker = Worker()
    workers = [worker, Worker()]

    write = sys.stdout.write
    flush = sys.stdout.flush

    items = [interpret_argument(worker, argument) for argument in arguments]

    main_process_paths = set(path for name, path in list_module_paths())
    file_watcher = Filesystem()

    while True:
        # import_order = improve_order(import_order, dangers)
        # print('Importing {}'.format(module_names))
        t0 = time()
        with contextlib.nested(*workers):
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

            successes = failures = 0
            worker_fds = {w.fileno(): w for w in workers}

            poller = select.epoll()
            for w in workers:
                if names:
                    name = names.pop()
                    w.start(capture_stdout_stderr, run_tests_of, name)
                    # w.start(run_tests_of, name)
                    poller.register(w, select.EPOLLIN)
            while worker_fds:
                for fd, flags in poller.poll():
                    w = worker_fds[fd]
                    result = w.next()
                    if result is StopIteration:
                        if names:
                            name = names.pop()
                            w.start(capture_stdout_stderr, run_tests_of, name)
                            # w.start(run_tests_of, name)
                        else:
                            poller.unregister(w)
                            del worker_fds[fd]
                    elif isinstance(result, str):
                        write('.')
                        flush()
                        successes += 1
                    else:
                        pretty_print_exception(*result)
                        flush()
                        failures += 1
            paths = [path for name_, path in worker.call(list_module_paths)]
        print()
        dt = time() - t0
        if failures:
            tally = red('{} of {} tests failed'.format(
                failures, successes + failures))
        else:
            tally = green('All {} tests passed'.format(successes))
        print('{} in {:.2f} seconds'.format(tally, dt))

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
            for w in workers:
                w.close()
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

stdout_banner = ' stdout '.center(72, '-')
stderr_banner = ' stderr '.center(72, '-')
plain_banner = '-' * 72

def pretty_print_exception(character, name, message, frames, out='', err=''):
    print()
    out = out.rstrip()
    err = err.rstrip()
    if out:
        print(stdout_banner)
        print(green(out))
    if err:
        print(stderr_banner)
        print(yellow(err))
    if out or err:
        print(plain_banner)
    for tup in frames:
        filename, line_number, function_name, text = tup
        a = '  {} line {} in'.format(filename, line_number)
        b = '{}'.format(function_name)
        f = '{}\n  {}' if (len(a) + len(b) > 78) else '{} {}'
        print(f.format(a, b))
        print('   ', blue(text))
    print(red('{}: {}'.format(name, message)))
    print()

def black(text): # ';47' does bg color
    return '\033[1;30m' + str(text) + '\033[0m'

def red(text):
    return '\033[1;31m' + str(text) + '\033[0m'

def green(text):
    return '\033[1;32m' + str(text) + '\033[0m'

def yellow(text):
    return '\033[1;33m' + str(text) + '\033[0m'

def blue(text):
    return '\033[1;35m' + str(text) + '\033[0m'
