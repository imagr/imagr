These are notes on the support for installing macOS using the `startosinstall` tool in "Install macOS Sierra.app" and "Install macOS High Sierra.app".

#### Workflow component:

```xml
    <key>workflows</key>
    <array>
        <dict>
            <key>components</key>
            <array>
                <dict>
                    <key>type</key>
                    <string>startosinstall</string>
                    <key>url</key>
                    <string>http://imagr.fake.com/installers/Install%20macOS%20High%20Sierra-10.13.dmg</string>
                </dict>
            </array>
            <key>description</key>
            <string>Installs High Sierra.</string>
            <key>name</key>
            <string>Install High Sierra</string>
        </dict>
    </array>
```

`url` must point to a disk image containing an Install macOS.app at the root.

This must be the **last** component in a given workflow; `startosinstall` will force a restart when it finishes setting up the macOS install; no subsequent workflow components will be executed.

Optional `additional_startosinstall_options`:

```xml
        <dict>
            <key>type</key>
            <string>startosinstall</string>
            <key>url</key>
      	    <string>http://imagr.fake.com/installers/Install%20macOS%20High%20Sierra-10.13.dmg</string>
            <key>additional_startosinstall_options</key>
            <array>
                <string>--converttoapfs</string>
                <string>NO</string>
            </array>
        </dict>
```

Optional `additional_package_urls`:

```xml
        <dict>
            <key>type</key>
            <string>startosinstall</string>
            <key>url</key>
            <string>http://imagr.fake.com/installers/Install%20macOS%20High%20Sierra-10.13.dmg</string>
            <key>additional_package_urls</key>
            <array>
                <string>http://imagr.fake.com/pkgs/AdminAccount.pkg</string>
                <string>http://imagr.fake.com/pkgs/SuppressSetupAssistant.pkg</string>
                <string>http://imagr.fake.com/pkgs/munkitools.pkg</string>
                <string>http://imagr.fake.com/pkgs/munki_kickstart.pkg</string>
            </array>
        </dict>
```

#### Additional package notes

Additional packages must be flat distribution-style packages. I did not find they needed to be signed.

As of 10.13 release, specifying more than one additional package appears to be broken; `startosinstall` doesn't seem to properly stage all the packages.

Paths for all given packages are added to macOS Install Data/InstallInfo.plist under the "Additional Installs" key, but not all are actually copied to the paths indicated. When the machine restarts after the macOS install is set up, the installer complains that "The path /System/Installation/Packages/OSInstall.mpkg appears to be missing or damaged." and tells you to restart and try again.

If you then restart to a different volume (locally attached or a network boot) you can see the problem. I tried to install four additional packages. macOS Install Data/InstallInfo.plist lists all four:

```xml
    <key>Additional Installers</key>
    <array>
        <string>UnwrappedInstallers/78d4e18c246101ac030409a3b28cf1ba6006055e/Adminaccount.pkg</string>
        <string>UnwrappedInstallers/56609c54df6cc13597ea94d2ffd30540d7027dc7/SuppressSetupAssistant.pkg</string>
        <string>UnwrappedInstallers/a04a3ba6f46deddca73b98679d09d2e41a95b2fa/munkitools.pkg</string>
        <string>UnwrappedInstallers/6a0b81670c8f340ee2c51c98aa0572f5a8aa055b/munki_kickstart.pkg</string>
    </array>
```

but the actual UnwrappedInstallers directory only has two of the packages:

```
$ ls -al macOS\ Install\ Data/UnwrappedInstallers/
total 0
drwxr-xr-x   4 root  wheel  136 Oct 11 10:11 .
drwxr-xr-x@ 16 root  wheel  544 Oct 11 10:13 ..
drwxr-xr-x   3 root  wheel  102 Oct 11 10:12 56609c54df6cc13597ea94d2ffd30540d7027dc7
drwxr-xr-x   3 root  wheel  102 Oct 11 10:12 6a0b81670c8f340ee2c51c98aa0572f5a8aa055b
```

I can manually copy the missing packages to the paths listed in InstallInfo.plist and then if I restart into the macOS Installer environment, install proceeds successfully and the extra packages are installed, although with some UI bugs.

One other bug: The additional packages are installed after the machine boots into the new OS for the first time. The mechanism that does the install appears to ignore the restart flag if it's set on any of the packages. I included the munkitools.pkg in my additional packages. It was successfully installed, but since there was no reboot after its install, Munki bootstrapping didn't actually work or kick in until after I manually restarted the machine one more time.

Assuming Apple eventually fixes these bugs, this should be a really useful way to deploy. But until then...


#### Alternate workflow with additional packages

Since there are serious bugs in 10.13's `startosinstall` with regard to additional packages, and since 10.12's `startosinstall` does not support additional packages at all, I present an alternate workflow:

```xml
    <dict>
        <key>components</key>
        <array>
            <dict>
                <key>first_boot</key>
                <true/>
                <key>type</key>
                <string>package</string>
                <key>url</key>
                <string>http://imagr.fake.com/pkgs/Adminaccount.pkg</string>
            </dict>
            <dict>
                <key>first_boot</key>
                <true/>
                <key>type</key>
                <string>package</string>
                <key>url</key>
                <string>http://imagr.fake.com/pkgs/SuppressSetupAssistant.pkg</string>
            </dict>
            <dict>
                <key>first_boot</key>
                <true/>
                <key>type</key>
                <string>package</string>
                <key>url</key>
                <string>http://imagr.fake.com/pkgs/munkitools.pkg</string>
            </dict>
            <dict>
                <key>first_boot</key>
                <true/>
                <key>type</key>
                <string>package</string>
                <key>url</key>
                <string>http://imagr.fake.com/pkgs/munki_kickstart.pkg</string>
            </dict>
            <dict>
                <key>type</key>
                <string>startosinstall</string>
                <key>url</key>
                <string>http://imagr.fake.com/installers/Install%20macOS%20High%20Sierra-10.13.dmg</string>
            </dict>
        </array>
        <key>description</key>
        <string>Installs High Sierra, installing additional packages at first boot.</string>
        <key>name</key>
        <string>Install High Sierra 2</string>
    </dict>
```

This uses package components that install at first boot. These are cached on the target disk (which might be empty to start) and then a macOS install is kicked off.

Brief testing shows this works (at least for 10.13 installs), but the UI is bad:
After the macOS install is complete and the machine boots to the new OS, it sits at a black screen while the cached packages are installed: LoginLog.app does not display a UI.

#### Testing notes

Clone this repo locally:  
`git clone https://github.com/gregneagle/imagr.git gregneagle-imagr`

In the same directory as the cloned repo, make a `config.mk` file. Recommended contents:

```
BUILD=Testing
STARTTERMINAL=True
APP="/Applications/Install macOS Sierra.app" # if you are building on Sierra
APP="/Applications/Install macOS High Sierra.app" # if you are building on HS
URL="http://imagr.fake.com/test_workflows.plist" # substitute your URL
INDEX="5007" # substitute your index
NBI="startosinstall_testing_Imagr" # substitute your nbi name
```

`make nbi` to build a (NetInstall-style) nbi containing Imagr. Transfer the resulting nbi (which is by default created on your Desktop) to your NetBoot server and perform the needed incantations to get your NetBoot server to offer this nbi.

Since we set `STARTTERMINAL=True` in the Makefile override, when this nbi boots it will open a terminal window instead of starting Imagr. This lets us see logging and debugging info. Launch Imagr like so:

```
/System/Installation/Packages/Imagr.app/Contents/MacOS/Imagr
```

To test later updates to the code, you don't have to go through the lengthy `make nbi` process again; you can just do `make update` as long as you left a copy of the nbi in its original location (again, Desktop by default). You'd then copy the updated nbi to the NetBoot server and test again.

