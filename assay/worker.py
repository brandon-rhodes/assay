"""A worker process that can respond to commands."""

import os
import socket
import sys
import unix
from types import GeneratorType

_enough = 1024 * 1024
_python3 = (sys.version_info.major >= 3)

if _python3:
    import pickle
else:
    import cPickle as pickle

class Worker(object):
    """An object in the main process for communicating with one worker."""

    def __init__(self):
        sock, child_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_DGRAM)

        unix.close_on_exec(sock.fileno())
        child_pid = os.fork()
        if not child_pid:
            python = sys.executable
            n = str(child_sock.fileno())
            os.setpgrp()  # prevent worker from receiving Ctrl-C
            os.execvp(python, [python, '-m', 'assay.worker', n])

        child_sock.close()

        self.pids = [child_pid]
        self.sock = sock

    def _send(self, obj):
        self.sock.send(pickle.dumps(obj))

    def _recv(self):
        return pickle.loads(self.sock.recv(_enough))

    def push(self):
        """Have the worker push a new subprocess on top of the stack."""
        self.pids.append(self.call(push))

    def pop(self):
        """Kill the top subprocess and pop it from the stack."""
        unix.kill_dash_9(self.pids.pop())
        assert self.next() == 'worker process popped'

    def call(self, function, *args, **kw):
        """Run a function in the worker process and return its result."""
        self._send((function, args, kw))
        return self._recv()

    def start(self, generator, *args, **kw):
        """Start a generator in the worker process."""
        self._send((generator, args, kw))

    def next(self):
        """Return the next item from the generator given to `start()`."""
        return self._recv()

    def fileno(self):
        """Return the incoming file descriptor, for `epoll()` objects."""
        return self.sock.fileno()

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
        self.sock.close()

def push():
    """Fork a child worker, who will own the pipe until it exits."""
    child_pid = os.fork()
    if not child_pid:
        return os.getpid()
    os.waitpid(child_pid, 0)
    return 'worker process popped'

def worker_process(sock_fd):
    """Run functions piped to us from the parent process.

    Both `to_parent` and `from_parent` should be integer file
    descriptors of the pipes connecting us to the parent process.

    """
    sock = socket.fromfd(sock_fd, socket.AF_UNIX, socket.SOCK_DGRAM)

    while True:
        function, args, kw = pickle.loads(sock.recv(_enough))
        result = function(*args, **kw)
        if isinstance(result, GeneratorType):
            for item in result:
                sock.send(pickle.dumps(item, 2))
            sock.send(pickle.dumps(StopIteration, 2))
        else:
            sock.send(pickle.dumps(result, 2))

if __name__ == '__main__':
    try:
        worker_process(int(sys.argv[1]))
    except KeyboardInterrupt:
        pass
