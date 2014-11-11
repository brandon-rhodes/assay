"""A worker process that can respond to commands."""

import os
import sys
import unix
from types import GeneratorType

_python3 = (sys.version_info.major >= 3)

if _python3:
    import pickle
else:
    import cPickle as pickle

class Worker(object):
    """An object in the main process for communicating with one worker."""

    def __init__(self):
        from_parent, to_worker = os.pipe()
        from_worker, to_parent = os.pipe()

        unix.close_on_exec(to_worker)
        unix.close_on_exec(from_worker)

        worker_pid = os.fork()
        if not worker_pid:
            os.setpgrp()  # prevent worker from receiving Ctrl-C
            os.execvp(sys.executable, [sys.executable, '-m', 'assay.worker',
                                       str(to_parent), str(from_parent)])

        os.close(to_parent)
        os.close(from_parent)

        self.pids = [worker_pid]
        self.to_worker = os.fdopen(to_worker, 'wb')
        self.from_worker = os.fdopen(from_worker, 'rb', 0)

    def push(self):
        """Have the worker push a new subprocess on top of the stack."""
        self.pids.append(self.call(os.fork))

    def pop(self):
        """Kill the top subprocess and pop it from the stack."""
        unix.kill_dash_9(self.pids.pop())
        assert pickle.load(self.from_worker) == self.pids[-1]
        # sock = self.sock
        # sock.setblocking(False)
        # while sock.recv():
        #     pass
        # sock.setblocking(True)

    def call(self, function, *args, **kw):
        """Run a function in the worker process and return its result."""
        pickle.dump((function, args, kw), self.to_worker)
        self.to_worker.flush()
        return pickle.load(self.from_worker)

    def start(self, generator, *args, **kw):
        """Start a generator in the worker process."""
        pickle.dump((generator, args, kw), self.to_worker)
        self.to_worker.flush()

    def next(self):
        """Return the next item from the generator given to `start()`."""
        return pickle.load(self.from_worker)

    def fileno(self):
        """Return the incoming file descriptor, for `epoll()` objects."""
        return self.from_worker.fileno()

    def __enter__(self):
        """During a 'with' statement, run commands in a clone of the worker."""
        self.push()

    def __exit__(self, a,b,c):
        """When the 'with' statement ends, have the clone exit."""
        self.pop()

    def close(self):
        """Kill the worker and close our file descriptors."""
        while self.pids:
            unix.kill_dash_9(self.pids.pop())
        self.to_worker.close()
        self.from_worker.close()

def worker_process(to_parent, from_parent):
    """Run functions piped to us from the parent process.

    Both `to_parent` and `from_parent` should be integer file
    descriptors of the pipes connecting us to the parent process.

    """
    to_parent = os.fdopen(to_parent, 'wb')
    from_parent = os.fdopen(from_parent, 'rb')

    while True:
        function, args, kw = pickle.load(from_parent)
        result = function(*args, **kw)
        if function is os.fork:
            if result:
                os.waitpid(result, 0)
            result = os.getpid()
        elif isinstance(result, GeneratorType):
            for item in result:
                pickle.dump(item, to_parent, 2)
                to_parent.flush()
            result = StopIteration
        pickle.dump(result, to_parent, 2)
        to_parent.flush()

if __name__ == '__main__':
    try:
        worker_process(int(sys.argv[1]), int(sys.argv[2]))
    except KeyboardInterrupt:
        pass
