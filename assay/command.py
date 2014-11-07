"""Support direct invocation from the command line."""

import argparse
import sys
from . import monitor

def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('name', nargs='+',
                        help='directory, package, or module to test')
    args = parser.parse_args()
    monitor.main_loop(args.name, True)
