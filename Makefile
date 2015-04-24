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
	curl -fsSL https://bitbucket.org/bruienne/autonbi/raw/master/AutoNBI.py -o ./AutoNBI.py
	chmod 755 ./AutoNBI.py

clean:
	rm -rf build

clean-pkgs:
	sudo rm -rf Packages

clean-all: clean clean-pkgs
	rm -rf AutoNBI.py
	rm -rf *.pyc
	rm -rf FoundationPlist.py
	rm -rf com.grahamgilbert.Imagr.plist

config:
	defaults write $(shell pwd)/com.grahamgilbert.Imagr serverurl $(URL)

deps: autonbi foundation

dmg: build
	hdiutil create -size 32m -fs HFS+ -volname "Imagr" Imagr.dmg
	hdiutil attach Imagr.dmg
	cp -r ./build/Release/Imagr.app /Volumes/Imagr
	hdiutil detach /Volumes/Imagr
	hdiutil convert Imagr.dmg -format UDZO -o Imagr-compressed.dmg
	mv Imagr-compressed.dmg Imagr-$(shell /usr/bin/defaults read `pwd`/build/Release/Imagr.app/Contents/Info.plist CFBundleShortVersionString).dmg
	rm Imagr.dmg

foundation:
	curl -fsSL https://raw.githubusercontent.com/munki/munki/master/code/client/munkilib/FoundationPlist.py -o ./FoundationPlist.py
	chmod 755 ./FoundationPlist.py

nbi: clean-pkgs build
	(if [ ! -f ./com.grahamgilbert.Imagr.plist ]; then make config; fi)
	(if [ ! -f ./AutoNBI.py ]; then make autonbi; fi)
	(if [ ! -f ./FoundationPlist.py ]; then make foundation; fi)
	mkdir -p Packages/Extras
	printf '%s\n%s' '#!/bin/bash' '/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr' > Packages/Extras/rc.imaging
	cp ./com.grahamgilbert.Imagr.plist Packages/
	cp -r ./build/Release/Imagr.app ./Packages
	sudo chown -R root:wheel Packages/*
	sudo chmod -R 755 Packages/*
	sudo ./AutoNBI.py -e -p -s $(APP) -f Packages -d $(OUTPUT) -n $(NBI)
