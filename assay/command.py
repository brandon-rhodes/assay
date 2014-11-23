"""Support direct invocation from the command line."""

from __future__ import print_function

import argparse
import os
import sys
from . import monitor, unix

def main():
    os.environ['PYTHONDONTWRITEBYTECODE'] = 'please'
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('name', nargs='+',
        help='directory, package, or module to test')
    parser.add_argument('--batch', action='store_true',
        help='run tests once, then exit with success or failure')
    args = parser.parse_args()
    try:
        with unix.configure_tty() as isatty:
            monitor.main_loop(args.name, args.batch or not isatty)
    except monitor.Restart:
        print()
        print(' Restart '.center(79, '='))
        executable = sys.executable
        os.execvp(executable, [executable, '-m', 'assay'] + sys.argv[1:])
    except KeyboardInterrupt:
        sys.stdout.write('\n')
