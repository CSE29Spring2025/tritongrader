#!/bin/bash

if [[ "$#" -ne "1" ]]; then
    echo "Usage: ./run_test.sh <test_name>"
    exit 1
fi

docker run --rm -v $(pwd)/cases/$1/submission:/autograder/submission -v $(pwd)/cases/$1/grader:/autograder/source e2egrader 