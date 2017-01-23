#!/bin/bash

cd $(dirname "$0")
PYTHONPATH=. coverage-2.7 run -m assay.tests "$@" && coverage html -i
echo '==========='
PYTHONPATH=. python -m assay.tests "$@"
