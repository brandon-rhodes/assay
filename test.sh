#!/bin/bash

cd $(dirname "$0")
PYTHONPATH=. python2 -m assay.tests "$@" &&
PYTHONPATH=. python3 -m assay.tests "$@" &&
pyflakes assay/*.py
