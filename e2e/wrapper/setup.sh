#!/bin/sh

adduser student --no-create-home --disabled-password --gecos ""
chmod -R o= /autograder
pip install -r /autograder/source/requirements.txt
mkdir -p /autograder/results