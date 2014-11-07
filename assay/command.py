"""Support direct invocation from the command line."""

import argparse
import os
import sys
from . import interactivity, monitor

def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('name', nargs='+',
                        help='directory, package, or module to test')
    args = parser.parse_args()
    try:
        with interactivity.configure_tty() as is_interactive:
            monitor.main_loop(args.name, is_interactive)
    except monitor.Restart:
        executable = sys.executable
        os.execvp(executable, [executable, '-m', 'assay'] + sys.argv[1:])
