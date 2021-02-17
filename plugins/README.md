# Mediator Plugins

Mediator's extensible reverse shell gives you more control than just the OS's shell that you're connected to. This is possible through the use of plugins, which can be called like any other command once you are connected to a reverse shell.

## Included plugins:

Mediator includes some plugins by default. Below is information on the included plugins and their usage:

### *push*

Description: Push a file from the operator's host to the target host.

Usage: `push <operator_path> <target_path>`

Example: `push recon_script.sh .`

### *pull*

Description: Pull a file from the target host to the operator's host.

Usage: `pull <target_path> <operator_path>`

Example: `pull forensics.zip forensics/host1.zip`

## Adding new plugins:

Plugins are contained in a single Python class. Every plugin should follow the CommandPlugin class interface. You will need to define methods for what will be run on the handler, windowsTarget, and linuxTarget systems when the plugin is called. You also need to have a method that declares the name of the plugin as it would appear on the command line when you execute it.

Once you have the file containing your plugin class in the plugins directory, you need to add it to the plugin module's \_\_init\_\_.py file so it will be found when importing plugins. You just need to add an import statement like the one below:

```python3
from .<filename> import <PluginClass>
```

Please refer to the included plugins for reference when creating your own.
