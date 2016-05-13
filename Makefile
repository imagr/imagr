# Makefile for Imagr related tasks
# User configurable variables below
#################################################

URL="http://192.168.178.135/imagr_config.plist"
REPORTURL=none
APP="/Applications/Install OS X El Capitan.app"
OUTPUT=~/Desktop
NBI="Imagr"
ARGS= --enable-nbi --add-python
BUILD=Release
AUTONBIURL=https://bitbucket.org/bruienne/autonbi/raw/master/AutoNBI.py
AUTONBIRAMDISK=False
AUTONBIRCNBURL=https://bitbucket.org/bruienne/autonbi/raw/f1e4e9c9688b766e73ed6e7633d2f4e7d1c223cf/rc.netboot
FOUNDATIONPLISTURL=https://raw.githubusercontent.com/munki/munki/master/code/client/munkilib/FoundationPlist.py
INDEX="5001"
VALIDATE=True
SYSLOG=none

-include config.mk

ifeq ($(AUTONBIRAMDISK),True)
	ARGS += " --ramdisk"
endif

#################################################

build: clean
	xcodebuild -configuration Release

autonbi:
	if [ ! -f ./AutoNBI.py ]; then \
		curl -fsSL $(AUTONBIURL) -o ./AutoNBI.py; \
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
ifeq ($(VALIDATE),True)
	./validateplist $(URL)
endif
	/usr/libexec/PlistBuddy -c 'Add :serverurl string "$(URL)"' com.grahamgilbert.Imagr.plist
ifneq ($(REPORTURL),none)
	/usr/libexec/PlistBuddy -c 'Add :reporturl string "$(REPORTURL)"' com.grahamgilbert.Imagr.plist
endif
ifneq ($(SYSLOG),none)
	/usr/libexec/PlistBuddy -c 'Add :syslog string "$(SYSLOG)"' com.grahamgilbert.Imagr.plist
endif

deps: autonbi foundation

dmg: build
	rm -f ./Imagr*.dmg
	rm -rf /tmp/imagr-build
	mkdir -p /tmp/imagr-build/Tools
	cp ./Readme.md /tmp/imagr-build
	cp ./Makefile /tmp/imagr-build/Tools
	cp -R ./build/Release/Imagr.app /tmp/imagr-build
	cp ./validateplist /tmp/imagr-build/Tools
	cp ./get_locale /tmp/imagr-build/Tools
	chmod +x /tmp/imagr-build/Tools/validateplist
	chmod +x /tmp/imagr-build/Tools/get_locale
	hdiutil create -srcfolder /tmp/imagr-build -volname "Imagr" -format UDZO -o Imagr.dmg
	mv Imagr.dmg \
		"Imagr-$(shell /usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "./build/Release/Imagr.app/Contents/Info.plist").dmg"
	rm -rf /tmp/imagr-build

foundation:
	if [ ! -f ./FoundationPlist.py ]; then \
		curl -fsSL $(FOUNDATIONPLISTURL) -o ./FoundationPlist.py; \
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
	sudo ./AutoNBI.py $(ARGS) --source $(APP) --folder Packages --destination $(OUTPUT) --name $(NBI) --index $(INDEX)
	$(MAKE) clean-all

update: clean-pkgs autonbi foundation config pkg-dir
	sudo ./AutoNBI.py --source $(OUTPUT)/$(NBI).nbi/NetInstall.dmg --folder Packages --name $(NBI) --index $(INDEX)
	$(MAKE) clean-all
