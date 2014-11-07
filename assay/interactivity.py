"""Support for users interacting with the terminal."""

import fcntl
import os
import sys
import termios
import tty
from contextlib import contextmanager

@contextmanager
def configure_tty():
    """Configure the terminal to give us keystrokes, not whole lines.

    By putting the terminal into non-blocking mode, turning off echo,
    and turning off canonical line interpretation, it becomes easy to
    run ``stdin.read()`` to see each keystroke the user types.  We also
    re-open ``stdin`` in unbuffered mode so that several keystrokes
    arriving at once will not be read into an internal buffer and
    thereby become invisible to ``epoll()``.

    """
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if is_interactive:
        fd = sys.stdin.fileno()
        sys.stdin = os.fdopen(fd, 'r', 0)

        original_fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, original_fl | os.O_NONBLOCK)

        original_mode = termios.tcgetattr(fd)
        mode = list(original_mode)
        mode[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON)
        mode[tty.CC][termios.VMIN] = 1
        mode[tty.CC][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSAFLUSH, mode)

    try:
        yield is_interactive
    finally:
        if is_interactive:
            fcntl.fcntl(fd, fcntl.F_SETFL, original_fl)
            termios.tcsetattr(fd, termios.TCSAFLUSH, original_mode)
