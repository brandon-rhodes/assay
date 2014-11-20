#!/bin/bash

cd $(dirname "$0")
PYTHONPATH=. coverage-2.7 run -m assay.tests && coverage html
echo '==========='
PYTHONPATH=. python3.4 -m assay.tests
