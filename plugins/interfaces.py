"""
File: interfaces.py
Author: C.J. May
Description: Using the provided interfaces, you can perform tasks on the target host outside of the capability of the shell you are connected to. This file contains an interface for adding custom commands to the shell.
"""
from abc import ABC, abstractmethod

class CommandInterface(ABC):
    @abstractmethod
    def handler(self, argv):
        """Code to be executed by the handler when the command is called"""
        return

    @abstractmethod
    def windowsTarget(self, argv):
        """Code to be executed by the windows target when the command is called"""
        return

    @abstractmethod
    def linuxTarget(self, argv):
        """Code to be executed by the linux target when the command is called"""
        return

    @abstractmethod
    def __repr__(self):
        """Return the name of the command as it would appear in the shell (ex. return "nmap")"""
        return
