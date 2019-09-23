How to play

Build Imagr.app with an embedded Python framework. See ../relocatable-python-notes.md for more info. Copy that app into the imagr folder inside this folder.

Edit imagr/com.grahamgilbert.Imagr.plist to point to your Imagr server.

Run ./make_dmg.sh to build a disk image, or copy the contents of the imagr folder to a USB (or other external) drive. Name (or rename) the volume "imagr".

Scenario 1:

Boot a machine into Recovery.
Connect the external drive you prepared above.
Open the Terminal.
Type `/Volumes/imagr/run`

Scenario 2:

Copy the dmg you generated to a web server.
Boot a machine into Recovery.
Open the Terminal.
Type `hdiutil attach <URL_for_the_dmg>`
Type `/Volumes/imagr/run`
