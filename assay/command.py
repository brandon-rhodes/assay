"""Support direct invocation from the command line."""

from __future__ import print_function
import argparse
import os
import sys
from .monitor import main_loop
from .worker import TransformIntoWorker, worker_task

def main():
    parser = argparse.ArgumentParser(prog='assay')
    parser.description = 'Fast testing framework'
    parser.add_argument('module', nargs='+', help='module or package to test')
    args = parser.parse_args()
    if 'PYTHONDONTWRITEBYTECODE' not in os.environ:
        print('Restarting Python to disable *.pyc imports')
        os.environ['PYTHONDONTWRITEBYTECODE'] = 'FORGREATJUSTICE'
        executable = sys.executable
        os.execvp(executable, [executable, '-m', 'assay'] + sys.argv[1:])
    try:
        main_loop(args.module)
    except TransformIntoWorker as pipes:
        pass
    else:
        return
    worker_task(pipes)
