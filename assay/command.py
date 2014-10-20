"""Support direct invocation from the command line."""

import argparse
import sys
from .monitor import main_loop
from .worker import TransformIntoWorker, worker_task

def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('name', nargs='+',
                        help='directory, package, or module to test')
    args = parser.parse_args()
    try:
        main_loop(args.name)
    except TransformIntoWorker as e:
        pipes = e.args
    else:
        return
    worker_task(pipes)
