#!/usr/bin/env python3

import pyseccomp as seccomp
import errno
import os
import sys
import socket

# Restrict network access
filter = seccomp.SyscallFilter(seccomp.ALLOW)
for network in [socket.AF_INET, socket.AF_INET6]:
    filter.add_rule(
            seccomp.ERRNO(errno.EACCES),
            "socket",
            seccomp.Arg(0, seccomp.EQ, network),
)
filter.load()

# Restrict file access and superuser privileges
os.setresuid(1000, 1000, 1000)  # We assume 1000 is "student"
os.setresgid(1000, 1000, 1000)

os.execvp(sys.argv[1], sys.argv[1:])
