# Makefile for Imagr related tasks
# User configurable variables below
#################################################

URL="http://192.168.178.135/imagr_config.plist"
APP="/Applications/Install OS X Yosemite.app"
OUTPUT=~/Desktop
NBI="Imagr"
ARGS= -e -p
BUILD=Release

-include config.mk

#################################################

build: clean
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
	rm -rf Imagr.app

run: build
	sudo build/Release/Imagr.app/Contents/MacOS/Imagr

config:
	rm -f com.grahamgilbert.Imagr.plist
	/usr/libexec/PlistBuddy -c 'Add :serverurl string "$(URL)"' com.grahamgilbert.Imagr.plist

deps: autonbi foundation

dmg: build
	rm -f ./Imagr*.dmg
	hdiutil create -srcfolder ./build/Release/Imagr.app -volname "Imagr" -format UDZO -o Imagr.dmg
	mv Imagr.dmg \
		"Imagr-$(shell /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "./build/Release/Imagr.app/Contents/Info.plist").dmg"

foundation:
	if [ ! -f ./FoundationPlist.py ]; then \
		curl -fsSL https://raw.githubusercontent.com/munki/munki/master/code/client/munkilib/FoundationPlist.py -o ./FoundationPlist.py; \
		chmod 755 ./FoundationPlist.py; \
	fi

dl:
	rm -f ./Imagr*.dmg
	rm -rf Imagr.app
	curl -sL -o ./Imagr.dmg --connect-timeout 30 $$(curl -s \
		https://api.github.com/repos/grahamgilbert/imagr/releases | \
		python -c 'import json,sys;obj=json.load(sys.stdin); \
		print obj[0]["assets"][0]["browser_download_url"]')
	hdiutil attach Imagr.dmg
	cp -r /Volumes/Imagr/Imagr.app .
	hdiutil detach /Volumes/Imagr
	rm ./Imagr.dmg	

pkg-dir:
	mkdir -p Packages/Extras
	printf '%s\n%s' '#!/bin/bash' '/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr' > Packages/Extras/rc.imaging
	cp ./com.grahamgilbert.Imagr.plist Packages/
ifeq ($(BUILD),Release)
	$(MAKE) dl
	cp -r ./Imagr.app ./Packages
else ifeq ($(BUILD),Testing)
	$(MAKE) build
	cp -r ./build/Release/Imagr.app ./Packages
else
	@echo "BUILD variable not set properly."
	exit 1
endif
	sudo chown -R root:wheel Packages/*
	sudo chmod -R 755 Packages/*

nbi: clean-pkgs autonbi foundation config pkg-dir
	sudo ./AutoNBI.py $(ARGS) -s $(APP) -f Packages -d $(OUTPUT) -n $(NBI)
	$(MAKE) clean-all

update: clean-pkgs build autonbi foundation config pkg-dir
	sudo ./AutoNBI.py -s $(OUTPUT)/$(NBI).nbi/NetInstall.dmg -f Packages
	$(MAKE) clean-all