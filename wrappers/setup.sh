#!/bin/sh -e
apt update
apt upgrade -y
# TODO add any extra dependencies of your autograder here
apt install -y python3-zstd build-essential
adduser student --no-create-home --disabled-password --gecos ""
chmod -R o= /autograder
# TODO perform any other setup, if necessary