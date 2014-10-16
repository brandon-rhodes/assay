"""Support direct invocation from the command line."""

import argparse
from .monitor import main_loop
from .worker import TransformIntoWorker, worker_task

def main():
    parser = argparse.ArgumentParser(description='Fast testing framework.')
    parser.add_argument('module', help='module or package to test')
    args = parser.parse_args()
    try:
        main_loop(args.module)
    except TransformIntoWorker as pipes:
        pass
    else:
        return
    worker_task(pipes)
