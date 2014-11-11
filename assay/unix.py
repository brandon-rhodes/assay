"""Support for users interacting with the terminal."""

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
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if is_interactive:
        fd = sys.stdin.fileno()
        original_mode = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    try:
        yield is_interactive
    finally:
        if is_interactive:
            termios.tcsetattr(fd, termios.TCSAFLUSH, original_mode)

def close_on_exec(fd):
    """Set the close-on-exec flag of the file descriptor `fd`."""
    fcntl.fcntl(fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

def cpu_count():
    """Return the number of CPUs on the system."""
    if os.path.exists('/proc/cpuinfo'):
        with open('/proc/cpuinfo') as f:
            return f.read().count('\nbogomips')
    return 2

def discard_input(fd):
    """Discard all bytes waiting to be read from a given file descriptor."""
    fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
    try:
        os.read(fd, _everything)
    except OSError:
        pass
    fcntl.fcntl(fd, fcntl.F_SETFL, 0)

def kill_dash_9(pid):
    """Kill a process with a signal that cannot be caught or ignored."""
    os.kill(pid, signal.SIGKILL)

class EPoll(object):
    """File descriptor polling object that returns objects, not integers."""

    def __init__(self):
        self.fdmap = {}
        self.poller = select.epoll()

    def register(self, obj, flags=select.EPOLLIN):
        fd = obj.fileno()
        self.fdmap[fd] = obj
        self.poller.register(fd, flags)

    def unregister(self, obj):
        fd = obj.fileno()
        del self.fdmap[fd]
        self.poller.unregister(fd)

    def events(self):
        while True:
            for fd, flags in self.poller.poll():
                yield self.fdmap[fd], flags
