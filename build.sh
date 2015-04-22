#!/bin/bash

# Simple build script for creating the current version of imagr for distribution.

source_path=$(dirname "${0}")
cd $source_path

# Build imagr using default "release" build
xcodebuild

# Create an initial disk image (32 megs)
hdiutil create -size 32m -fs HFS+ -volname "Imagr" Imagr.dmg

# Mount the disk image
hdiutil attach Imagr.dmg

# Copy imagr.app to dmg
cp -r ./build/Release/Imagr.app /Volumes/Imagr

# Unmount the disk image
hdiutil detach /Volumes/Imagr

# Convert the disk image to read-only and add version number
version=`defaults read $(pwd)/build/Release/Imagr.app/Contents/Info.plist CFBundleShortVersionString`
hdiutil convert Imagr.dmg -format UDZO -o Imagr-compressed.dmg
mv Imagr-compressed.dmg Imagr-$version.dmg

# Remove temp dmg
rm Imagr.dmg
