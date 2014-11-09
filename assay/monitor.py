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
ctrl_d = '\x04'

def write(string):
    """Send `string` immediately to standard output, without buffering."""
    os.write(stdout_fd, string)

def main_loop(arguments, is_interactive):
    """Run and report on tests while also letting the user type commands."""

    main_process_paths = set(path for name, path in list_module_paths())

    file_watcher = Filesystem()
    file_watcher.add_paths(main_process_paths)

    poller = unix.EPoll()
    poller.register(file_watcher)
    if is_interactive:
        poller.register(sys.stdin)

    workers = []
    try:
        for i in range(unix.cpu_count()):
            worker = Worker()
            workers.append(worker)
            poller.register(worker)

        paths_under_test = set()
        runner = run_all_tests(arguments, workers, paths_under_test)
        runner.next()

        for source, flags in poller.events():

            if isinstance(source, Worker):
                try:
                    runner.send(source)
                except StopIteration:
                    if not is_interactive:
                        break
                    file_watcher.add_paths(paths_under_test)
                    write('Watching {} paths...'.format(len(paths_under_test)))

            elif source is sys.stdin:
                for keystroke in sys.stdin.read():
                    print('got {}'.format(keystroke))
                    if keystroke in 'q' + ctrl_d:
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

            # import_order = improve_order(import_order, dangers)
            # module_paths, events = worker(import_modules, import_order)
    finally:
        for worker in workers:
            worker.close()

def run_all_tests(arguments, workers, paths_under_test):
    worker = workers[0]
    running_workers = set()
    names = []
    t0 = time()
    successes = failures = 0

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
            elif result == '.':
                write('.')
                successes += 1
            else:
                pretty_print_exception(*result)
                failures += 1

    finally:
        for worker in workers:
            worker.pop()

    dt = time() - t0
    if failures:
        tally = red('{} of {} tests failed'.format(
            failures, successes + failures))
    else:
        tally = green('All {} tests passed'.format(successes))
    write('\n{} in {:.2f} seconds\n'.format(tally, dt))

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
