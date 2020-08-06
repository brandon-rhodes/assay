"""Support for users interacting with the terminal."""

import errno
import fcntl
import os
import select
import signal
import sys
import termios
import tty
from contextlib import contextmanager

_everything = 1024 * 1024

@contextmanager
def configure_tty():
    """Configure the terminal to give us keystrokes, not whole lines.

    By turning off echo and canonical line interpretation, a read from
    standard input will immediately see each keystroke the user types.

    """
    isatty = sys.stdin.isatty() and sys.stdout.isatty()
    if isatty:
        fd = sys.stdin.fileno()
        original_mode = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    try:
        yield isatty
    finally:
        if isatty:
            termios.tcsetattr(fd, termios.TCSAFLUSH, original_mode)

def close_on_exec(fd):
    """Set the close-on-exec flag of the file descriptor `fd`."""
    fcntl.fcntl(fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

def keep_on_exec(fd):
    """Clear the close-on-exec flag of the file descriptor `fd`."""
    fcntl.fcntl(fd, fcntl.F_SETFD, 0)

def cpu_count():
    """Return the number of CPUs on the system."""
    if os.path.exists('/proc/cpuinfo'):
        with open('/proc/cpuinfo') as f:
            count = f.read().count('\nbogomips')
        if count:
            return count
    return 2

def discard_input(fileobj, bufsize):
    """Discard all bytes queued for input on `fileobj`.

    Bytes queued in the operating system are disposed of through an
    ``os.read()``, and bytes in our own buffers by replacing the object.

    """
    fd = fileobj.fileno()
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    try:
        os.read(fd, _everything)
    except OSError:
        pass
    fcntl.fcntl(fd, fcntl.F_SETFL, 0)
    return os.fdopen(os.dup(fd), fileobj.mode, bufsize)

def kill_dash_9(pid):
    """Kill a process with a signal that cannot be caught or ignored."""
    os.kill(pid, signal.SIGKILL)

class EPoll(object):
    """File descriptor polling object that returns objects, not integers."""

    def __init__(self):
        self.fdmap = {}
        try:
            self.poller = select.epoll()
        except AttributeError:
            self.poller = select.poll()  # TODO: does this work on OS X?

    def register(self, obj, flags=None):
        if flags is None:
            try:
                flags = select.EPOLLIN
            except AttributeError:
                flags = select.POLLIN
        fd = obj.fileno()
        self.fdmap[fd] = obj
        self.poller.register(fd, flags)

    def unregister(self, obj):
        fd = obj.fileno()
        del self.fdmap[fd]
        self.poller.unregister(fd)

    def events(self):
        while True:
            try:
                for fd, flags in self.poller.poll():
                    yield self.fdmap[fd], flags
            except IOError as e:
                if e.errno != errno.EINTR:
                    raise

