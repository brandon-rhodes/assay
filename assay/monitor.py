"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import contextlib
import os
import sys
from time import time
from . import unix
from .discovery import interpret_argument, search_argument
from .filesystem import Filesystem
from .importation import import_module, improve_order, list_module_paths
from .runner import capture_stdout_stderr, run_tests_of
from .worker import Worker

class Restart(BaseException):
    """Tell ``main()`` that we need to restart."""

stdout_fd = sys.stdin.fileno()

def write(string):
    """Send `string` immediately to standard output, without buffering."""
    os.write(stdout_fd, string)

def main_loop(arguments, is_interactive):
    """Run and report on tests while also letting the user type commands."""

    main_process_paths = set(path for name, path in list_module_paths())

    file_watcher = Filesystem()
    file_watcher.add_paths(main_process_paths)

    workers = [Worker(), Worker()]

    poller = unix.EPoll()
    poller.register(file_watcher)
    for worker in workers:
        poller.register(worker)
    if is_interactive:
        poller.register(sys.stdin)

    paths_under_test = set()
    runner = run_all_tests(arguments, workers, paths_under_test)
    runner.next()

    try:
        for source, flags in poller.events():

            if isinstance(source, Worker):
                try:
                    runner.send(source)
                except StopIteration:
                    print('\n\n')
                    file_watcher.add_paths(paths_under_test)

            elif source is sys.stdin:
                for keystroke in sys.stdin.read():
                    print('got {}'.format(keystroke))
                    if keystroke == 'q':
                        sys.exit()
                    elif keystroke == 'r':
                        raise Restart()

            elif source is file_watcher:
                changes = file_watcher.read()
                paths = [os.path.join(directory, filename)
                         for directory, filename in changes]
                main_process_changes = main_process_paths.intersection(paths)
                if main_process_changes:
                    example_path = main_process_changes.pop()
                    write('\nAssay has been modified: {}'.format(example_path))
                    raise Restart()
                runner.close()

                paths_under_test = set()
                runner = run_all_tests(arguments, workers, paths_under_test)
                runner.next()

            continue

            # import_order = improve_order(import_order, dangers)
            # module_paths, events = worker(import_modules, import_order)
            # print('Importing {}'.format(module_names))
            t0 = time()
            with contextlib.nested(*workers):
                # t0 = time()
                # module_paths, events = worker(import_modules, import_order)
                # pprint(events)
                # print('  {} seconds'.format(time() - t0))
                # print()

                successes = failures = 0

                for w in workers:
                    if names:
                        name = names.pop()
                        w.start(capture_stdout_stderr, run_tests_of, name)
                        # w.start(run_tests_of, name)
                        poller.register(w, select.EPOLLIN)
                while worker_fds:
                    for fd, flags in poller.poll():
                        w = worker_fds.get(fd)
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

            print()
            print('Running tests')
    finally:
        for worker in workers:
            worker.close()

def run_all_tests(arguments, workers, paths_under_test):
    worker = workers[0]
    running_workers = set()
    names = []

    for argument in arguments:
        import_path, import_name = interpret_argument(worker, argument)
        more_names = search_argument(import_path, import_name)
        names.extend(more_names)

    def give_work_to(worker):
        if names:
            name = names.pop()
            worker.start(capture_stdout_stderr, run_tests_of, name)
            running_workers.add(worker)
        else:
            running_workers.remove(worker)
            paths = [path for name, path in worker.call(list_module_paths)]
            paths_under_test.update(paths)

    for worker in workers:
        worker.push()

    try:
        for worker in workers:
            give_work_to(worker)

        while running_workers:
            worker = yield
            result = worker.next()
            if result is StopIteration:
                give_work_to(worker)
                continue
            if isinstance(result, str):
                write(result)
            else:
                write(repr(result))

    finally:
        for worker in workers:
            worker.pop()

    write('\n\n')

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
