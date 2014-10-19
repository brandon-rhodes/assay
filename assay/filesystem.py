import ctypes
import os
import struct
import time

# Experimental inotify support for the sake of illustration.

IN_MODIFY = 0x02
_libc = None

def _setup_libc():
    global _libc
    if _libc is not None:
        return
    ctypes.cdll.LoadLibrary('libc.so.6')
    _libc = ctypes.CDLL('libc.so.6', use_errno=True)
    _libc.inotify_add_watch.argtypes = [
        ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
    _libc.inotify_add_watch.restype = ctypes.c_int

def wait_on(paths):
    # TODO: auto-detect when the OS does not offer libc or libc does not
    # offer inotify_wait, and fall back to looping_wait_on().
    _setup_libc()
    return _inotify_wait_on(paths)

def looping_wait_on(paths):
    start = time.time()
    changed_paths = []
    while not changed_paths:
        time.sleep(0.5)
        changed_paths = [path for path in paths
                         if os.stat(path).st_mtime > start]
    return changed_paths

FORMAT = 'iIII'
SIZE = struct.calcsize(FORMAT)

class FileWatcher(object):

    def __init__(self):
        _setup_libc()
        self.paths = set()
        self.descriptors = {}
        self.fd = _libc.inotify_init()
        if self.fd == -1:
            message = os.strerror(ctypes.get_errno())
            raise OSError('inotify_init() error: {}'.format(message))

    def add_paths(self, paths):
        fd = self.fd
        new_paths = set(path.encode('ascii') for path in paths) - self.paths
        for path in new_paths:
            d = _libc.inotify_add_watch(fd, path, 0x2)
            self.paths.add(path)
            self.descriptors[d] = path
            d = _libc.inotify_add_watch(fd, os.path.dirname(path), 0x2)
            self.descriptors[d] = os.path.dirname(path)

    def wait(self):
        data = os.read(self.fd, 1024)

        # TODO: continue with some more reads with 0.1 second timeouts
        # to empty the list of roughly-simultaneous events before
        # closing our file descriptor and returning?

        while data:
            d, mask, cookie, name_length = struct.unpack(FORMAT, data[:SIZE])
            j = SIZE + name_length
            name = data[SIZE:j].rstrip('\0')
            data = data[j:]
            print(d, mask, cookie, name)
        return [self.descriptors[d].decode('ascii')]
