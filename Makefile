ifeq ($(OS),Windows_NT)
	TARGET := WINDOWS
else
	UNAME_S := $(shell uname -s)
 ifeq ($(UNAME_S),Linux)
	TARGET := LINUX
 endif
 ifeq ($(UNAME_S),Darwin)
	TARGET := OSX
 else
	@echo ERROR: Could not detect OS version -- not in [Windows, Linux, Darwin]
	@exit 1
 endif
endif

all: handler windowsTarget linuxTarget
	@echo Done making executables for all clients.

handler:
	@echo Creating standalone executable for handler...
	@cd ./pyinstaller
	@pyinstaller --distpath . --log-level CRITICAL pyinstaller/handler.spec

windowsTarget:
ifeq ($(TARGET),WINDOWS)
	@echo Creating standalone executable for windowsTarget...
	@cd pyinstaller
	@pyinstaller --distpath . --log-level CRITICAL pyinstaller/windowsTarget.spec
else
	@echo WARNING: Pyinstaller must be run on a Windows host to create a standalone executable for windowsTarget.py
endif


linuxTarget:
ifeq ($(TARGET),WINDOWS)
	@echo WARNING: Pyinstaller must be run on a Linux host to create a standalone executable for linuxTarget.py
else
	@echo Creating standalone executable for linuxTarget...
	@cd pyinstaller
	@pyinstaller --distpath . --log-level CRITICAL pyinstaller/linuxTarget.spec
endif
