#!/bin/sh

adduser student --no-create-home --disabled-password --gecos ""
chmod -R o= /autograder
pip install -r /autograder/source/requirements.txt
chmod +x /autograder/source/harness.py
