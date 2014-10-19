import ctypes
import os
import time
from struct import calcsize, unpack

# Experimental inotify support for the sake of illustration.

MASK = (0x00000008 # IN_CLOSE_WRITE
      | 0x00000080 # IN_MOVED_TO
      | 0x00000200 # IN_DELETE
      | 0x00000400 # IN_DELETE_SELF
      | 0x00000800 # IN_MOVE_SELF
      )
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
SIZE = calcsize(FORMAT)

class FileWatcher(object):

    def __init__(self):
        _setup_libc()
        self.paths = set()
        self.descriptors = {}
        self.fd = _libc.inotify_init()
        if self.fd == -1:
            message = os.strerror(ctypes.get_errno())
            raise OSError('inotify_init() error: {}'.format(message))

    def add_paths(self, file_paths):
        fd = self.fd
        paths = set(os.path.dirname(path) for path in file_paths) - self.paths
        for path in paths:
            d = _libc.inotify_add_watch(fd, path, MASK)
            self.paths.add(path)
            self.descriptors[d] = path

    def wait(self):
        changes = []
        while not changes:
            data = os.read(self.fd, 8192)
            while data:
                d, mask, cookie, name_length = unpack(FORMAT, data[:SIZE])
                directory = self.descriptors[d]
                j = SIZE + name_length
                name = data[SIZE:j].rstrip('\0')
                data = data[j:]
                if is_not_relevant(name):
                    continue
                changes.append((directory, name))
        return changes

def is_not_relevant(filename):
    """Return whether we can ignore changes to a file with this filename."""
    return filename.endswith('~') or filename.startswith('.#')
