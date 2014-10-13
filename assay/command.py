"""Support direct invocation from the command line."""

import argparse
from .monitor import main_loop

def main():
    parser = argparse.ArgumentParser(description='Fast testing framework.')
    parser.add_argument('module', help='module or package to test')
    args = parser.parse_args()
    main_loop(args.module)
