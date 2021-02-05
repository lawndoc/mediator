import os, sys, inspect
from pkgutil import iter_modules
from pathlib import Path
from importlib import import_module

# add plugins dir to path
plugins_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile( inspect.currentframe() ))[0]))
if plugins_folder not in sys.path:
    sys.path.insert(0, plugins_folder)

from interfaces import CommandPlugin

# iterate through the modules in the plugins dir
for (_, module_name, _) in iter_modules([plugins_folder]):

    # import the module and iterate through its attributes
    module = import_module(f"{__name__}.{module_name}")
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if inspect.isclass(attribute):
            if issubclass(attribute, CommandPlugin):
                # Add the class to this package's variables
                globals()[attribute_name] = attribute

del iter_modules
del Path
del import_module
