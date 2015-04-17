# Imagr

Imagr is an application designed to be run from a NetInstall environment created with [AutoNBI](https://bitbucket.org/bruienne/autonbi/src). It is able to restore a disk image and install packages on a target volume. It is not intended to be a replacement for tools such as DeployStudio, but is able to perform some of their more commonly used functions to allow organisations to run more complicated workflows than just basic NetRestore without the need for OS X in the datacentre.

This is a Python application, so Python will need to be included in your NetInstall.

This is pre-release code and under heavy development. There are bugs if you don't follow the magic path. Bug reports are welcomed, pull requests are even better.

## Features

### Workflows

Taking inspiration from DeployStudio, Imagr supports multiple workflows - these workflows currently consist of an image and optionally one or more packages.

### Imaging

The image is deployed using ASR over HTTP. An image that is produced by AutoDMG will work perfectly.

### Packages

Packages are currently installed at first boot, and must be flat packages. In the future, support for installing packages from a dmg and at imaging time is planned to support those use cases.

## Configuration

Imagr gets its configuration from a plist that is accessible over HTTP. This URL is configured in a plist that will be looked for in the following locations (from top to bottom) - the key is ``serverurl``:

* ~/Library/Preferences/com.grahamgilbert.Imagr.plist
* /Library/Preferences/com.grahamgilbert.Imagr.plist
* /System/Installation/Packages/com.grahamgilbert.Imagr.plist

### The plist

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
      </array>
    </dict>
  </array>
</dict>
</plist>
```

The above plist will configure Imagr. The majority of the options should be obvious.

#### Password

The password is a SHA hash - designed to stop customers from accidently imaging their computers, not to keep the crown jewels safe! To generate one:

```
$ python -c 'import hashlib; print hashlib.sha512("YOURPASSWORDHERE").hexdigest()'
```
