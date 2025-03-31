#!/bin/bash

if [[ "$#" -ne "1" ]]; then
    echo "Usage: ./run_test.sh <test_name>"
    exit 1
fi

docker run --rm -v $(pwd)/$1:/autograder/submission autograder