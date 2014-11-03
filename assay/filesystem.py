import ctypes
import re
import time
from collections import defaultdict
from keyword import iskeyword
from os import listdir, read, stat, strerror
from os.path import dirname, isdir, join
from struct import calcsize, unpack

IN_CLOSE_WRITE = 0x00000008
IN_MOVED_TO =    0x00000080
IN_CREATE =      0x00000100
IN_DELETE =      0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF =   0x00000800
MASK = IN_CLOSE_WRITE | IN_MOVED_TO | IN_DELETE | IN_DELETE_SELF | IN_MOVE_SELF
_libc = None

identifier_re_match = re.compile('[A-Za-z_][A-Za-z0-9_]*').match

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
        changed_paths = [path for path in paths if stat(path).st_mtime > start]
    return changed_paths

FORMAT = 'iIII'
SIZE = calcsize(FORMAT)

class Filesystem(object):
    """A cached and sanitized filesystem view, automatically kept up-to-date.

    """
    def __init__(self):
        _setup_libc()
        self.fd = _libc.inotify_init()
        if self.fd == -1:
            message = strerror(ctypes.get_errno())
            raise OSError('inotify_init() error: {}'.format(message))
        self.descriptors = {}
        self._isdir_cache = _isdir_dict()
        self.isdir = self._isdir_cache.__getitem__
        self.paths = set()

    def search_directory(self, path):
        pass

    def list(self, directory):
        listing = self.listings.get(directory)
        if listing is None:
            filenames = listdir(directory)
            listing = [join(directory, filename) for filename in filenames
                       if is_interesting(filename)]
            self.listing[directory] = listing
        return listing

    def add_paths(self, file_paths):
        fd = self.fd
        paths = set(dirname(path) for path in file_paths) - self.paths
        for path in paths:
            d = _libc.inotify_add_watch(fd, path, MASK)
            self.paths.add(path)
            self.descriptors[d] = path

    def wait(self):
        changes = []
        while not changes:
            data = read(self.fd, 8192)
            while data:
                d, mask, cookie, name_length = unpack(FORMAT, data[:SIZE])
                directory = self.descriptors[d]
                j = SIZE + name_length
                name = data[SIZE:j].rstrip('\0')
                data = data[j:]
                if not is_interesting(name):
                    continue
                changes.append((directory, name))
        return changes

def module_name_of(filename):
    if filename.endswith('.py'):
        base = filename[:-3]
        if is_identifier(base):
            return base
    return None

def is_identifier(name):
    return identifier_re_match(name) and not iskeyword(name)

def is_interesting(name):
    return not (name.startswith('.') or name.endswith('~'))

class _isdir_dict(dict):
    def __missing__(self, key):
        value = isdir(key)
        self[key] = value
        return value
