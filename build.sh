#!/bin/bash

# Simple build script for creating the current version of imagr for distribution.

source_path=$(dirname "${0}")
cd $source_path

# Build imagr using default "release" build
xcodebuild

# Create an initial disk image (32 megs)
hdiutil create -size 32m -fs HFS+ -volname "imagr" imagr.dmg

# Mount the disk image
hdiutil attach imagr.dmg

# Copy imagr.app to dmg
cp -r ./build/Release/Imagr.app /Volumes/imagr

# Unmount the disk image
hdiutil detach /Volumes/imagr

# Convert the disk image to read-only and add version number
version=`defaults read $(pwd)/build/Release/Imagr.app/Contents/Info.plist CFBundleShortVersionString`
hdiutil convert imagr.dmg -format UDZO -o imagr-compressed.dmg
mv imagr-compressed.dmg imagr-$version.dmg

# Remove temp dmg
rm imagr.dmg