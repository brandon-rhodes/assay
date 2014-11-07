"""Support for users interacting with the terminal."""

import fcntl
import os
import signal
import sys
import termios
import tty
from contextlib import contextmanager

@contextmanager
def configure_tty():
    """Configure the terminal to give us keystrokes, not whole lines.

    By putting the terminal into non-blocking mode, turning off echo,
    and turning off canonical line interpretation, it becomes easy to
    run ``stdin.read()`` to see each keystroke the user types.

    """
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if is_interactive:
        fd = sys.stdin.fileno()

        original_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, original_fl | os.O_NONBLOCK)

        original_mode = termios.tcgetattr(fd)
        tty.setcbreak(fd)

    try:
        yield is_interactive
    finally:
        if is_interactive:
            fcntl.fcntl(fd, fcntl.F_SETFL, original_fl)
            termios.tcsetattr(fd, termios.TCSAFLUSH, original_mode)

def close_on_exec(fd):
    """Set the close-on-exec flag of the file descriptor `fd`."""
    fcntl.fcntl(fd, fcntl.F_SETFD, fcntl.FD_CLOEXEC)

def kill_dash_9(pid):
    """Kill a process with a signal that cannot be caught or ignored."""
    os.kill(pid, signal.SIGKILL)
