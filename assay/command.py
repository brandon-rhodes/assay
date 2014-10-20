"""Support direct invocation from the command line."""

from __future__ import print_function
import argparse
import sys
from .monitor import main_loop
from .worker import TransformIntoWorker, worker_task

def main():
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('name', nargs='+',
                        help='directory, package, or module to test')
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    try:
        main_loop(args.module)
    except TransformIntoWorker as pipes:
        pass
    else:
        return
    worker_task(pipes)
