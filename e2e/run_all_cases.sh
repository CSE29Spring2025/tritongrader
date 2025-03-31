#!/bin/bash

for testcase in cases/*; do
    echo "--- RUNNING $(basename $testcase) ---"
    ./run_test.sh $(basename $testcase)
done