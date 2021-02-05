from interfaces import CommandPlugin

class PushCommand(CommandPlugin):
    def handler(argv):
        print("Ran handler code")
        return

    def windowsTarget(argv):
        print("Ran windows code")
        return

    def linuxTarget(argv):
        print("Ran linux code")
        return

    def name():
        return "push"
