"""A worker process that can respond to commands."""

import os
import sys
from functools import wraps
from importlib import import_module

python3 = (sys.version_info.major >= 3)

if python3:
    import pickle
else:
    import cPickle as pickle

class TransformIntoWorker(BaseException):
    """Pop everything off of the stack and become a worker."""

remote_functions = {}

def remote(function):
    """Mark a Worker method so that it runs in the forked worker."""

    name = function.__name__
    remote_functions[name] = function

    @wraps(function)
    def wrapper(self, *args, **kw):
        pickle.dump((name, args, kw), self.to_child)
        self.to_child.flush()
        return pickle.load(self.from_child)

    return wrapper

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

    def __enter__(self):
        assert self.push() == 'worker process pushed'

    def __exit__(self, a,b,c):
        assert self.pop() == 'worker process popped'

    @remote
    def push():
        child_pid = os.fork()
        if not child_pid:
            return 'worker process pushed'
        os.waitpid(child_pid, 0)
        return 'worker process popped'

    @remote
    def pop():
        """This is implemented as a special case in worker_task(), below."""

    @remote
    def __call__(function, *args, **kw):
        return function(*args, **kw)

    # @remote
    # def list_modules():
    #     return list(sys.modules)

    # @remote
    # def import_modules(names):
    #     for name in names:
    #         import_module(name)

def worker_task(pipes):
    """Run remote functions until being told to exit."""

    to_parent, from_parent = pipes.args

    while True:
        try:
            name, args, kw = pickle.load(from_parent)
        except EOFError:
            os._exit(0)
        if name == 'pop':
            os._exit(0)
        function = remote_functions[name]
        result = function(*args, **kw)
        pickle.dump(result, to_parent)
        to_parent.flush()
