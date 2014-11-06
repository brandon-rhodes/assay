"""A worker process that can respond to commands."""

import os
import signal
import sys
from types import GeneratorType

python3 = (sys.version_info.major >= 3)

if python3:
    import pickle
else:
    import cPickle as pickle

class TransformIntoWorker(BaseException):
    """Tell main() to pop everything off of the stack and become a worker."""

class Worker(object):

    def __init__(self):
        from_parent, to_child = os.pipe()
        from_child, to_parent = os.pipe()
        child_pid = os.fork()

        if not child_pid:
            os.close(to_child)
            os.close(from_child)
            to_parent = os.fdopen(to_parent, 'wb')
            from_parent = os.fdopen(from_parent, 'rb')
            raise TransformIntoWorker(to_parent, from_parent)

        self.pids = [child_pid]
        os.close(to_parent)
        os.close(from_parent)
        self.to_child = os.fdopen(to_child, 'wb')
        self.from_child = os.fdopen(from_child, 'rb', 0)

    def call(self, function, *args, **kw):
        """Run a function in the worker process and return its result."""
        pickle.dump((function, args, kw), self.to_child)
        self.to_child.flush()
        return pickle.load(self.from_child)

    def start(self, generator, *args, **kw):
        """Start a generator in the worker process."""
        pickle.dump((generator, args, kw), self.to_child)
        self.to_child.flush()

    def next(self):
        """Return the next item from the generator given to `start()`."""
        return pickle.load(self.from_child)

    def fileno(self):
        """Return the incoming file descriptor, for `epoll()` objects."""
        return self.from_child.fileno()

    def __enter__(self):
        """During a 'with' statement, run commands in a clone of the worker."""
        self.pids.append(self.call(push))

    def __exit__(self, a,b,c):
        """When the 'with' statement ends, have the clone exit."""
        os.kill(self.pids.pop(), signal.SIGKILL)
        assert self.next() == 'worker process popped'

    def close(self):
        """Kill the worker and close our file descriptors."""
        while self.pids:
            os.kill(self.pids.pop(), signal.SIGKILL)
        self.to_child.close()
        self.from_child.close()

def push():
    """Fork a child worker, who will own the pipe until it exits."""
    child_pid = os.fork()
    if not child_pid:
        return os.getpid()
    os.waitpid(child_pid, 0)
    return 'worker process popped'

def worker_task(pipes):
    """Run functions piped to us from the parent process.

    The main process produces a worker process by calling fork() and
    having the child process raise TransformIntoWorker, which pops the
    stack all the way out to assay.main.command() whose "try...except"
    clause catches the exception and calls this function instead.

    """
    to_parent, from_parent = pipes

    while True:
        function, args, kw = pickle.load(from_parent)
        result = function(*args, **kw)
        if isinstance(result, GeneratorType):
            for item in result:
                pickle.dump(item, to_parent, 2)
                to_parent.flush()
            pickle.dump(StopIteration, to_parent, 2)
            to_parent.flush()
        else:
            pickle.dump(result, to_parent, 2)
            to_parent.flush()
