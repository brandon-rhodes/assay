"""A worker process that can respond to commands."""

import os
import sys
from . import unix
from .fixes import _accumulating_reader
from types import GeneratorType

_python3 = sys.version_info >= (3,)

if _python3:
    import pickle
else:
    import cPickle as pickle

WORKER_TERMINATED = b'!'

# A crucial setting: the buffer size for input from a worker process.
# If we were to allow buffering of data from the worker, then the buffer
# might read ahead on the input stream and leave the descriptor looking
# empty from the point of view of epoll().
BUFSIZE = 0

class Worker(object):
    """An object in the main process for communicating with one worker."""

    def __init__(self):
        from_parent, to_worker = os.pipe()
        from_worker, to_parent = os.pipe()
        sync_from_worker, sync_to_parent = os.pipe()

        unix.close_on_exec(to_worker)
        unix.close_on_exec(from_worker)
        unix.close_on_exec(sync_from_worker)

        unix.keep_on_exec(from_parent)
        unix.keep_on_exec(to_parent)
        unix.keep_on_exec(sync_to_parent)

        worker_pid = os.fork()
        if not worker_pid:
            os.setpgrp()  # prevent worker from receiving Ctrl-C
            python = sys.executable
            os.execvp(python, [python, '-m', 'assay.worker', str(from_parent),
                               str(to_parent), str(sync_to_parent)])

        os.close(from_parent)
        os.close(to_parent)
        os.close(sync_to_parent)

        self.pids = [worker_pid]
        self.to_worker = os.fdopen(to_worker, 'wb')
        self.from_worker = os.fdopen(from_worker, 'rb', BUFSIZE)
        self.sync_from_worker = sync_from_worker

    def push(self):
        """Have the worker push a new subprocess on top of the stack."""
        self.pids.append(self.call(os.fork))

    def pop(self):
        """Kill the active worker subprocess and pop it from the stack.

        Because we might happen to kill a worker as it is in the middle
        of writing out a pickle, we listen on the separate "sync" pipe
        for the worker's parent to confirm that the worker has exited.
        Then we discard any left-over bytes on the data pipe.

        """
        unix.kill_dash_9(self.pids.pop())
        assert os.read(self.sync_from_worker, 1) == WORKER_TERMINATED
        # Subtle - worker could have died in mid-pickle:
        self.from_worker = unix.discard_input(self.from_worker, BUFSIZE)

    def call(self, function, *args, **kw):
        """Run a function in the worker process and return its result."""
        pickle.dump((function, args, kw), self.to_worker)
        self.to_worker.flush()
        return pickle.load(_accumulating_reader(self.from_worker))

    def start(self, generator, *args, **kw):
        """Start a generator in the worker process."""
        pickle.dump((generator, args, kw), self.to_worker)
        self.to_worker.flush()

    def next(self):
        """Return the next item from the generator given to `start()`."""
        return pickle.load(_accumulating_reader(self.from_worker))

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
        os.close(self.sync_from_worker)

def worker_process(from_parent, to_parent, sync_to_parent):
    """Run functions piped to us from the parent process.

    This is the entire control loop of an assay worker process, which is
    launched when this module is run with "-m" by the "Worker" class.
    It listens to a pipe over which it is given a series of functions to
    invoke, and sends back their return values.  Sometimes the function
    is `fork()`, in which case a worker child process is launched; in
    that case, the child takes control of the conversation, with the
    parent waiting idle and only resuming control of the conversation
    once the child is finished.

    Both `to_parent` and `from_parent` should be integer file
    descriptors of the pipes connecting us to the parent process.

    """
    to_parent = os.fdopen(to_parent, 'wb')
    from_parent = os.fdopen(from_parent, 'rb')

    while True:
        function, args, kw = pickle.load(_accumulating_reader(from_parent))
        result = function(*args, **kw)
        if function is os.fork:
            if result:
                os.waitpid(result, 0)
                # Subtle: worker can die with a command still inbound
                from_parent = unix.discard_input(from_parent, BUFSIZE)
                os.write(sync_to_parent, WORKER_TERMINATED)
                continue
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
        worker_process(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
    except KeyboardInterrupt:
        pass
