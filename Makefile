# Makefile for Imagr related tasks
# User configurable variables below
#################################################

URL="http://192.168.178.135/imagr_config.plist"
APP=/Applications/Install\ OS\ X\ Yosemite.app
OUTPUT=~/Desktop
NBI="Imagr"

#################################################


build:
	xcodebuild -configuration Release

autonbi:
	if [ ! -f ./AutoNBI.py ]; then \
		curl -fsSL https://bitbucket.org/bruienne/autonbi/raw/master/AutoNBI.py -o ./AutoNBI.py; \
		chmod 755 ./AutoNBI.py; \
	fi

clean:
	rm -rf build

clean-pkgs:
	sudo rm -rf Packages

clean-all: clean clean-pkgs
	rm -rf AutoNBI.py
	rm -rf com.grahamgilbert.Imagr.plist
	rm -rf FoundationPlist.py
	rm -rf FoundationPlist.pyc

config:
	defaults write $(shell pwd)/com.grahamgilbert.Imagr serverurl $(URL)

deps: autonbi foundation

dmg: build
	rm -f ./Imagr.dmg
	rm -f ./Imagr-compressed.dmg
	hdiutil create -size 32m -fs HFS+ -volname "Imagr" Imagr.dmg
	hdiutil attach Imagr.dmg
	cp -r ./build/Release/Imagr.app /Volumes/Imagr
	hdiutil detach /Volumes/Imagr
	hdiutil convert Imagr.dmg -format UDZO -o Imagr-compressed.dmg
	mv Imagr-compressed.dmg Imagr-$(shell /usr/bin/defaults read `pwd`/build/Release/Imagr.app/Contents/Info.plist CFBundleShortVersionString).dmg
	rm Imagr.dmg

foundation:
	if [ ! -f ./FoundationPlist.py ]; then \
		curl -fsSL https://raw.githubusercontent.com/munki/munki/master/code/client/munkilib/FoundationPlist.py -o ./FoundationPlist.py; \
		chmod 755 ./FoundationPlist.py; \
	fi

nbi: clean-pkgs build autonbi foundation config
	mkdir -p Packages/Extras
	printf '%s\n%s' '#!/bin/bash' '/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr' > Packages/Extras/rc.imaging
	cp ./com.grahamgilbert.Imagr.plist Packages/
	cp -r ./build/Release/Imagr.app ./Packages
	sudo chown -R root:wheel Packages/*
	sudo chmod -R 755 Packages/*
	sudo ./AutoNBI.py -e -p -s $(APP) -f Packages -d $(OUTPUT) -n $(NBI)
	if [ -f ./FoundationPlist.py ]; then \
		sudo rm FoundationPlist.py; \
	fi
	if [ -f ./FoundationPlist.pyc ]; then \
		sudo rm FoundationPlist.pyc; \
	fi
	if [ -f ./AutoNBI.py ]; then \
		sudo rm AutoNBI.py; \
	fi
	if [ -f ./com.grahamgilbert.Imagr.plist ]; then \
		rm com.grahamgilbert.Imagr.plist; \
	fi
	sudo rm -rf Packages
