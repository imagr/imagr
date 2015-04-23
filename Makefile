all: clean build

clean:
	rm -rf build

clean-pkgs:
	sudo rm -rf Packages

clean-all: clean clean-pkgs
	rm -rf AutoNBI.py

build:
	xcodebuild

deps: autonbi munkitools

autonbi:
	curl -fsSL https://bitbucket.org/bruienne/autonbi/raw/master/AutoNBI.py -o ./AutoNBI.py
	chmod 755 ./AutoNBI.py

munkitools:
	curl https://raw.githubusercontent.com/n8felton/Mac-OS-X-Scripts/master/munki/latest2_stable_admin.sh | bash

netboot: clean-pkgs
	mkdir -p Packages/Extras
	printf '%s\n%s' '#!/bin/bash' '/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr' >> Packages/Extras/rc.imaging
	cp com.grahamgilbert.Imagr.plist Packages/
	cp -r ./build/Release/Imagr.app ./Packages
	sudo chown -R root:wheel Packages/*
	sudo chmod -R 755 Packages/*
	sudo ./AutoNBI.py -e -p -s /Applications/Install\ OS\ X\ Yosemite.app -f Packages -d ~/Desktop -n Imagr
