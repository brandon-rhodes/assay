"""Monitor a package for changes and run its tests when it changes."""

from __future__ import print_function

import os
import sys
from . import unix
from .discovery import interpret_argument, search_argument
from .filesystem import Filesystem
from .importation import list_module_paths
from .reporting import BatchReporter, InteractiveReporter
from .runner import capture_stdout_stderr, run_tests_of
from .worker import Worker

class Restart(BaseException):
    """Tell ``main()`` that we need to restart."""

python3 = sys.version_info >= (3,)
stdin_fd = sys.stdin.fileno()
stdout_fd = sys.stdout.fileno()
ctrl_d = b'\x04'

def read_keystrokes():
    """Read user keystrokes from standard input."""
    keystrokes = os.read(stdin_fd, 1024)
    if python3:
        keystrokes = [keystrokes[i:i+1] for i in range(len(keystrokes))]
    return keystrokes

def write(string):
    """Send `string` immediately to standard output, without buffering."""
    os.write(stdout_fd, string.encode('ascii'))

def main_loop(arguments, batch_mode, verbose=False):
    """Run and report on tests while also letting the user type commands."""

    main_process_paths = set(path for name, path in list_module_paths())

    poller = unix.EPoll()
    if batch_mode:
        file_watcher = None
        reporter_class = BatchReporter
    else:
        file_watcher = Filesystem()
        file_watcher.add_paths(main_process_paths)
        poller.register(file_watcher)
        reporter_class = InteractiveReporter
        poller.register(sys.stdin)

    runner = None  # so our 'finally' clause does not explode
    workers = []
    try:
        for i in range(unix.cpu_count()):
            worker = Worker()
            workers.append(worker)
            poller.register(worker)

        paths_under_test = set()
        reporter = reporter_class(write)
        runner = runner_coroutine(arguments, workers, reporter,
                                  paths_under_test, verbose)
        next(runner)

        for source, flags in poller.events():

            if isinstance(source, Worker):
                try:
                    runner.send(source)
                except StopIteration:
                    if batch_mode:
                        exit(1 if reporter.errors else 0)
                    file_watcher.add_paths(paths_under_test)
                    #write('Watching {0} paths...'.format(len(paths_under_test)))

            elif source is sys.stdin:
                for keystroke in read_keystrokes():
                    if keystroke == b'q' or keystroke == ctrl_d:
                        print(' quit')
                        sys.exit(0)
                    elif keystroke == b'r':
                        raise Restart()
                    else:
                        reporter.process_keystroke(keystroke)

            elif source is file_watcher:
                changes = file_watcher.read()
                paths = [os.path.join(directory, filename)
                         for directory, filename in changes]
                main_process_changes = main_process_paths.intersection(paths)
                if main_process_changes:
                    example_path = main_process_changes.pop()
                    write('\nAssay has been modified: {0}'.format(example_path))
                    raise Restart()
                runner.close()

                if paths:
                    write('\n\nFile modified: {0}\n\n'.format(paths[0]))

                paths_under_test = set()
                reporter = reporter_class(write)
                runner = runner_coroutine(arguments, workers, reporter,
                                          paths_under_test, verbose)
                next(runner)

            # import_order = improve_order(import_order, dangers)
            # module_paths, events = worker(import_modules, import_order)
    finally:
        if runner is not None:
            runner.close()
        for worker in workers:
            worker.close()

def runner_coroutine(arguments, workers, reporter, paths_under_test,
                     verbose=False):
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
        else:
            running_workers.remove(worker)
            paths = [path for name, path in worker.call(list_module_paths)]
            paths_under_test.update(paths)

    for worker in workers:
        worker.push()

    try:
        for worker in workers:
            running_workers.add(worker)
            give_work_to(worker)

        while running_workers:
            worker = yield
            result = worker.next()
            if result is StopIteration:
                give_work_to(worker)
            else:
                reporter.report_result(result, verbose)

    finally:
        for worker in workers:
            worker.pop()

    reporter.summarize()
