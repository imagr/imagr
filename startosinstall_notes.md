Workflow component:

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

As of 10.13 release, specifying more than one additional package appears to be broken; `startosinstall` doesn't seem to properly stage all the packages.

Additional packages must be flat distribution-style packages. I did not find they needed to be signed.
