#!/bin/sh

adduser student --no-create-home --disabled-password --gecos ""
chmod -R o= /autograder/*

# Only for our tests
pip install -r /autograder/source/requirements.txt
