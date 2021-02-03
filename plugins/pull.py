from interfaces import CommandInterface

class PullCommand(CommandInterface):
    def handler(argv):
        print("Ran handler code")
        return

    def windowsTarget(argv):
        print("Ran windows code")
        return

    def linuxTarget(argv):
        print("Ran linux code")

    def name():
        return "pull"
