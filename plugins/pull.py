from interfaces import CommandInterface

class PullCommand(CommandInterface):
    def handler(self, argv):
        pass

    def windowsTarget(self, argv):
        pass

    def linuxTarget(self, argv):
        pass

    def __repr__(self):
        return "pull"
