# Mediator

Mediator is an end-to-end encrypted reverse shell that doesn't require port forwarding for the handler.

### Architecture:

Inspired by end-to-end encrypted chat applications, this reverse shell takes a unique approach to the client/server model of a reverse shell. This reverse shell uses:

1. A client reverse shell
2. A client hander/operator
3. A server that bridges the two connections

### Instructions:

**Server**

The client scripts can be run on Windows or Linux, but you'll need to stand up the server ([mediator.py](mediator.py)) on a Linux host. You can either run the server script with

```bash
$ python3 mediator.py
```

or you can build a Docker image with the provided [Dockerfile](Dockerfile) and run it in a container (make sure to publish ports 20000 and 20001).

**Target/Reverse Shell**

Make sure to set your server's address in the script, and then execute the target script on the target host with

```powershell
> python .\windowsTarget.py
```

or optionally create an exe with pyinstaller's `--onefile` flag.

**Handler/Operator**

Same instructions as the reverse shell (make sure you set the server's address).

