#!/bin/bash

cd $(dirname "$0")
PYTHONPATH=. python2.7 -m assay.tests
echo '==========='
PYTHONPATH=. python3.4 -m assay.tests
