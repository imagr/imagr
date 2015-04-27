# Imagr

Imagr is an application designed to be run from a NetInstall environment created with [AutoNBI](https://bitbucket.org/bruienne/autonbi/src). It is able to restore a disk image and install packages on a target volume. It is not intended to be a replacement for tools such as DeployStudio, but is able to perform some of their more commonly used functions to allow organisations to run more complicated workflows than just basic NetRestore without the need for OS X in the datacentre.

This is a Python application, so Python will need to be included in your NetInstall.

This is pre-release code and under heavy development. There are bugs if you don't follow the magic path. Bug reports are welcomed, pull requests are even better.

## Table of Contents

* [Features](#features)
	* [Workflows](#workflows)
	* [Imaging](#imaging)
	* [Packages](#packages)
	* [Scripts](#scripts)
* [Configuration](#configuration)
	* [The configuration plist](#the-configuration-plist)
	* [Password](#password)
	* [Restart Action](#restart-action)
	* [Startup Disk](#startup-disk)
* [Building a NetInstall](#building-a-netinstall)
	* [Automatic Creation Using Make](#automatic-creation-using-make)
	* [Manual Build Creation](#manual-build-creation)

## Features

### Workflows

Taking inspiration from DeployStudio, Imagr supports multiple workflows - these workflows currently consist of an image and optionally one or more packages.

### Imaging

The image is deployed using ASR over HTTP. An image that is produced by [AutoDMG](https://github.com/MagerValp/AutoDMG) will work perfectly.

### Packages

Packages can either be installed at first boot (the default) or pre first boot by using the following in the component in the configuration plist:

``` xml
<dict>
    <key>type</key>
    <string>package</string>
    <key>url</key>
    <string>http://192.168.178.135/MunkiTools.pkg</string>
    <key>pre_first_boot</key>
    <true/>
</dict>
```

### Scripts

Scripts can either be run at first boot (the default) or pre first boot by using the following in the component in the configuration plist:

``` xml
<dict>
    <key>type</key>
    <string>script</string>
    <key>content</key>
    <string>#!/bin/bash
/usr/bin/touch "{{target_volume}}/some_file"</string>
    <key>pre_first_boot</key>
    <true/>
</dict>
```

Any non-xml safe characters will need to be encoded, and if you need to refer to the target volume, use ``{{ target_volume}}``.

## Configuration

Imagr gets its configuration from a plist that is accessible over HTTP. This URL is configured in a plist that will be looked for in the following locations (from top to bottom) - the key is ``serverurl``:

* ``~/Library/Preferences/com.grahamgilbert.Imagr.plist``
* ``/Library/Preferences/com.grahamgilbert.Imagr.plist``
* ``/System/Installation/Packages/com.grahamgilbert.Imagr.plist``

Sample ``com.grahamgilbert.Imagr.plist``:
``` xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>serverurl</key>
  <string>http://192.168.178.135/imagr_config.plist</string>
</dict>
</plist>
```

### The configuration plist

Seen above as ``imagr_config.plist``. This file can be named anything but needs to match your ``serverurl``.

``` xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>password</key>
  <string>b109f3bbbc244eb82441917ed06d618b9008dd09b3befd1b5e07394c706a8bb980b1d7785e5976ec049b46df5f1326af5a2ea6d103fd07c95385ffab0cacbc86</string>
  <key>workflows</key>
  <array>
    <dict>
      <key>name</key>
      <string>Munki_10103</string>
      <key>description</key>
      <string>Deploys a 10.10.3 image with Munki Tools and it's configuration.</string>
      <key>components</key>
      <array>
        <dict>
          <key>type</key>
          <string>image</string>
          <key>url</key>
          <string>http://192.168.178.135/osx_custom_150410-10.10.3-14D131.hfs.dmg</string>
        </dict>
        <dict>
            <key>type</key>
            <string>package</string>
            <key>url</key>
            <string>http://192.168.178.135/MunkiTools.pkg</string>
        </dict>
        <dict>
            <key>type</key>
            <string>package</string>
            <key>url</key>
            <string>http://192.168.178.135/Munki_Config.pkg</string>
        </dict>
        <dict>
            <key>type</key>
            <string>package</string>
            <key>url</key>
            <string>http://192.168.178.135/clearReg.pkg</string>
        </dict>
				<dict>
					<key>type</key>
					<string>script</string>
					<key>content</key>
					<string>#!/bin/bash
echo "&lt;"
echo "{{target_volume}}"
/usr/bin/touch "{{target_volume}}/some_file"</string>
				</dict>
      </array>
    </dict>
  </array>
</dict>
</plist>
```

The above plist will configure Imagr. The majority of the options should be obvious.

#### Password

The password is a SHA hash - designed to stop customers from accidentally imaging their computers, not to keep the crown jewels safe! To generate one:

```
$ python -c 'import hashlib; print hashlib.sha512("YOURPASSWORDHERE").hexdigest()'
```

#### Restart Action

Each workflow can have a ``restart_action`` defined. If no ``restart_action`` is specified, Imagr will fall back to the default of ``restart``.

* ``restart``: Once the workflow is completed, Imagr will restart to the target volume.
* ``shutdown``: Once the workflow is completed, Imagr will set the startup disk to the target volume and shut the Mac down.
* ``none``: Once the workflow is completed, Imagr will present a dialog asking if the Mac should be shut down, restarted or if another workflow should be run.

#### Startup Disk

By default, Imagr will bless the target volume to set it as the startup volume. This is usually desirable, but in some cases you will want to not do this (for example, when using [createOSXinstallPkg](https://github.com/munki/createOSXinstallPkg)). To avoid this, use the following in your workflow:

``` xml
<key>bless_target</key>
<false/>
```

## Building a NetInstall

**Requirements:** Most of these are taken care of automatically with the included ``Makefile``.

* AutoNBI
	* We need the ``FoundationPlist`` module from [Munki](https://github.com/munki/munki)
	* A OS X Mavericks 10.9 (or later) Installer Application
* Xcode 6.0 or later (currently needed to build Imagr)


### Automatic Creation Using Make

The included ``Makefile`` makes the process of creating a NetInstall near painless. You will need Xcode 6.0 or later installed. We currently have a few defaults that you might wish to override. Defaults listed below descriptions.

* ``URL`` - The URL to your Imagr Configuration plist.
* ``APP`` - The path to your OS X installer. Quote this path when using command line arguments.
* ``OUTPUT`` - The output path of your NBI file. Do _not_ quote this path when using relative paths.
* ``NBI`` - The output name of your NBI file.

```
# Defaults
URL="http://192.168.178.135/imagr_config.plist"
APP="/Applications/Install OS X Yosemite.app"
OUTPUT=~/Desktop
NBI="Imagr"
```

You can change these default variables in the ``Makefile`` or via command line arguments. Just make sure and follow the including quote formatting, it is very important! The quotes might change when using command line arguments so please reference the examples below.


**Command Line Argument Examples:**

```
$ make nbi
$ make nbi URL="http://my_server/imagr_config.plist"
$ make nbi URL="http://my_server/imagr_config.plist" OUTPUT=~/Documents
$ make nbi URL="http://my_server/imagr_config.plist" APP="/Applications/Install OS X Mavericks.app" OUTPUT=/Volumes/data/temp/ NBI="myImagr"
```

### Manual Build Creation

Basic instructions for creating this NetInstall manually are located below.

1. Download and build Imagr. (Xcode 6.0 or later will need to be installed).

	```
	$ bash
	$ git clone https://github.com/grahamgilbert/imagr.git
	$ cd imagr
	$ xcodebuild -configuration Release
	```

	We should now have a running copy of Imagr located in the build/Release folder.

1. Download AutoNBI.

	```
	$ curl -fsSL https://bitbucket.org/bruienne/autonbi/raw/master/AutoNBI.py -o ./AutoNBI.py
	$ chmod 755 ./AutoNBI.py
	```
1. Download ``FoundationPlist.py`` to the current directory for AutoNBI.

	```
	$ curl -fsSL https://raw.githubusercontent.com/munki/munki/master/code/client/munkilib/FoundationPlist.py -o ./FoundationPlist.py
	$ chmod 755 FoundationPlist.py
	```

1. Create a Packages/Extras directory. This is necessary to make Imagr auto launch when your NetInstall has loaded.

	```
	$ mkdir -p Packages/Extras
	```

1. Create a ``rc.imaging`` file inside of the Extras directory. For greater details regarding the ``rc.imaging`` file visit this [blog post](http://grahamgilbert.com/blog/2015/04/13/more-fun-with-autonbi/).

	```
	$ printf '%s\n%s' '#!/bin/bash' '/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr' > Packages/Extras/rc.imaging
	```

1. Copy ``Imagr.app`` into the Packages directory.

	```
	$ cp -r ./build/Release/Imagr.app ./Packages
	```

1. Create your ``com.grahamgilbert.Imagr.plist`` file inside of the Packages directory.

	[See example above](#packages).

1. Verify your directory structure looks correct.

	```
	├── AutoNBI.py
	├── Packages
	│   ├── Extras
	│   │   └── rc.imaging
	│   ├── Imagr.app
	│   └── com.grahamgilbert.Imagr.plist
	```

1. Set file permissions.

	```
	$ sudo chown -R root:wheel Packages/*
	$ sudo chmod -R 755 Packages/*
	```

1. Build your image. Make sure and change your Installer path to a valid OS X installer. Fore more details on AutoNBI visit the project [README](https://bitbucket.org/bruienne/autonbi/src).

	```
	$ sudo ./AutoNBI.py -e -p -s /Applications/Install\ OS\ X\ Yosemite.app -f Packages -d ~/Desktop -n Imagr
	```

	This process will take a few minutes to build the environment.
