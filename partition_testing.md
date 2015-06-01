Testing 'eraseVolume' and 'partition' actions
=====

##eraseVolume

type: "eraseVolume"  
name: defaults to "Macintosh HD" if not specified  
format: defaults to "Journaled HFS+" if not specified  
**first_boot must be false**

These arguments are passed directly to `diskutil`, so any format provided by `diskutil listFileSystems` will be accepted.

Here are `components` keys for `eraseVolume` workflows:

```
				<dict>
					<key>type</key>
					<string>eraseVolume</string>
				</dict>
```

```
				<dict>
					<key>type</key>
					<string>eraseVolume</string>
					<key>name</key>
					<string>My Volume Name</string>
				</dict>
```

```
				<dict>
					<key>type</key>
					<string>eraseVolume</string>
					<key>name</key>
					<string>My Volume Name</string>
					<key>format</key>
					<string>Journaled HFS+</string>
				</dict>
```

##partition

type: "partition"  
map: defaults to "GPTFormat"  
partitions: array of dictionaries of partitions  
**first_boot must be false**  

###Each partition:
name: defaults to "Macintosh HD" if not specified  
format_type: defaults to "Journaled HFS+" if not specified  
size: defaults to "100%" if not specified  
**If size is specified in one partition, it must be specified for all partitions**  
target: one **and only one** partition must be chosen as a target for future actions  

Example `components` of `partition` workflows:

```
				<dict>
					<key>type</key>
					<string>partition</string>
					<key>map</key>
					<string>GPTFormat</string>
					<key>partitions</key>
					<array>
						<dict>
							<key>format_type</key>
							<string>Journaled HFS+</string>
							<key>name</key>
							<string>First</string>
							<key>size</key>
							<string>50%</string>
							<key>target</key>
							<true/>
						</dict>
						<dict>
							<key>format_type</key>
							<string>Journaled HFS+</string>
							<key>name</key>
							<string>Second</string>
							<key>size</key>
							<string>50%</string>
						</dict>
					</array>
				</dict>
```

```
				<dict>
					<key>type</key>
					<string>partition</string>
					<key>map</key>
					<string>GPTFormat</string>
					<key>partitions</key>
					<array>
						<dict>
							<key>format_type</key>
							<string>Journaled HFS+</string>
							<key>name</key>
							<string>Macintosh HD</string>
							<key>target</key>
							<true/>
						</dict>
					</array>
				</dict>
```

```
				<dict>
					<key>type</key>
					<string>partition</string>
					<key>map</key>
					<string>GPTFormat</string>
					<key>partitions</key>
					<array>
						<dict>
							<key>name</key>
							<string>Macintosh HD</string>
							<key>target</key>
							<true/>
						</dict>
					</array>
				</dict>
```