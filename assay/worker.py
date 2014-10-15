"""A worker process that can respond to commands."""

import os
import sys

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

            pickle.dump('ok', to_parent)
            to_parent.flush()

            raise TransformIntoWorker(to_parent, from_parent)

        os.close(to_parent)
        os.close(from_parent)
        self.to_child = os.fdopen(to_child, 'wb')
        self.from_child = os.fdopen(from_child, 'rb')

        assert pickle.load(self.from_child) == 'ok'

    def __call__(self, function, *args, **kw):
        """Run a function in the worker process and return its result."""
        pickle.dump((function, args, kw), self.to_child)
        self.to_child.flush()
        return pickle.load(self.from_child)

    def __enter__(self):
        """During a 'with' statement, run commands in a clone of the worker."""
        assert self(push) == 'worker process pushed'

    def __exit__(self, a,b,c):
        """When the 'with' statement ends, have the clone exit."""
        assert self(pop) == 'worker process popped'

def push():
    """Fork a child worker, who will own the pipe until it exits."""
    child_pid = os.fork()
    if not child_pid:
        return 'worker process pushed'
    os.waitpid(child_pid, 0)
    return 'worker process popped'

def pop():
    """This is implemented as a special case in worker_task(), below."""

def worker_task(pipes):
    """Run remote functions until being told to exit."""

    to_parent, from_parent = pipes.args

    while True:
        try:
            function, args, kw = pickle.load(from_parent)
        except EOFError:
            os._exit(0)
        if function is pop:
            os._exit(0)
        result = function(*args, **kw)
        pickle.dump(result, to_parent)
        to_parent.flush()
