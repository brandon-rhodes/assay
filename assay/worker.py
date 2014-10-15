"""A worker process that can respond to commands."""

import os
import pickle

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

            while True:
                break
            os._exit(0)

        os.close(to_parent)
        os.close(from_parent)
        self.to_child = os.fdopen(to_child, 'wb')
        self.from_child = os.fdopen(from_child, 'rb')

        assert pickle.load(self.from_child) == 'ok'

    def start(self):
        pass

    def import_modules(self, names):
        pass
