#!/bin/sh -e
apt update
apt upgrade -y
# TODO add any extra dependencies of your autograder here
apt install -y python3-zstd build-essential valgrind icdiff bat
adduser student --no-create-home --disabled-password --gecos ""
chmod -R o= /autograder
pip3 install --upgrade pip wheel
pip3 install --force-reinstall -r /autograder/source/requirements.txt
# TODO perform any other setup, if necessary
