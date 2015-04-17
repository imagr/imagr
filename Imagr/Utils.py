# -*- coding: utf-8 -*-
#
#  Utils.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

import urllib2
import hashlib
import os
import FoundationPlist
import math
import plistlib
import shutil
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import tempfile
import subprocess

def downloadFile(url):
    # Migrate this to requests to actually do a bit of cert validation. This
    # was lazy
    data = urllib2.urlopen(url)
    new_data = data.read()
    return new_data

def getPasswordHash(password):
    return hashlib.sha512(password).hexdigest()

def getServerURL():

    # Try the user's homedir
    try:
        NSLog("Trying Home Location")
        homedir = os.path.expanduser("~")
        plist = FoundationPlist.readPlist(os.path.join(homedir, "Library", "Preferences", "com.grahamgilbert.Imagr.plist"))
        return plist['serverurl']
    except:
        pass
    # Try the main prefs
    try:
        NSLog("Trying System Location")
        plist = FoundationPlist.readPlist(os.path.join("/Library", "Preferences", "com.grahamgilbert.Imagr.plist"))
        return plist['serverurl']
    except:
        pass

    # Hopefully we're in a netboot set, try in /System/Installation/Packages
    try:
        NSLog("Trying NetBoot Location")
        plist = FoundationPlist.readPlist(os.path.join("/System", "Installation", "Packages", "com.grahamgilbert.Imagr.plist"))
        return plist['serverurl']
    except:
        pass


def downloadAndInstallPackage(url, target):
    if os.path.basename(url).endswith('.dmg'):
        # We're going to mount the dmg
        dmgmountpoints = mountdmg(url)
        dmgmountpoint = dmgmountpoints[0]

        # Now we're going to go over everything that ends .pkg or
        # .mpkg and install it
        for package in os.listdir(dmgmountpoint):
            if package.endswith('.pkg') or package.endswith('.mpkg'):
                pkg = os.path.join(dmgmountpoint, package)
                installPkg(pkg, target)

        # Unmount it
        unmountdmg(dmgmountpoint)

    if os.path.basename(url).endswith('.pkg'):

        # Make our temp directory on the target
        temp_dir = tempfile.mkdtemp(dir=target)
        # Download it
        packagename = os.path.basename(url)
        downloaded_file = downloadChunks(url, os.path.join(temp_dir,
                                                        packagename))
        # Install it
        installPkg(downloaded_file, target)
        # Clean up after ourselves
        shutil.rmtree(temp_dir)


def installPkg(pkg, target):
    """
    Installs a package on a specific volume
    """
    installer_pool = NSAutoreleasePool.alloc().init()
    cmd = ['/usr/sbin/installer', '-pkg', pkg, '-target', target]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unusederr) = proc.communicate()
    if unusederr:
        NSLog(str(unusederr))
    del installer_pool

def mountdmg(dmgpath):
    """
    Attempts to mount the dmg at dmgpath
    and returns a list of mountpoints
    """
    mountpoints = []
    dmgname = os.path.basename(dmgpath)
    cmd = ['/usr/bin/hdiutil', 'attach', dmgpath, '-nobrowse', '-plist',
           '-owners', 'on']
    proc = subprocess.Popen(cmd, bufsize=-1,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (pliststr, err) = proc.communicate()
    if proc.returncode:
        print >> sys.stderr, 'Error: "%s" while mounting %s.' % (err, dmgname)
    if pliststr:
        plist = plistlib.readPlistFromString(pliststr)
        for entity in plist['system-entities']:
            if 'mount-point' in entity:
                mountpoints.append(entity['mount-point'])

    return mountpoints

def unmountdmg(mountpoint):
    """
    Unmounts the dmg at mountpoint
    """
    proc = subprocess.Popen(['/usr/bin/hdiutil', 'detach', mountpoint],
                            bufsize=-1, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    (unused_output, err) = proc.communicate()
    if proc.returncode:
        print >> sys.stderr, 'Polite unmount failed: %s' % err
        print >> sys.stderr, 'Attempting to force unmount %s' % mountpoint
        # try forcing the unmount
        retcode = subprocess.call(['/usr/bin/hdiutil', 'detach', mountpoint,
                                   '-force'])
        print('Unmounting successful...')
        if retcode:
            print >> sys.stderr, 'Failed to unmount %s' % mountpoint

def downloadPackage(url, target, number, package_count):
    package_name = str(number) +"-" +os.path.basename(url)
    os.umask(0002)
    #package_name = str(number) + '-' +package_name
    package_name = package_name.zfill(package_count)
    if not os.path.exists(os.path.join(target, "usr/local/first-boot/packages")):
        os.makedirs(os.path.join(target, "usr/local/first-boot/packages"))
    file = os.path.join(target, 'usr/local/first-boot/packages',package_name)
    output = downloadChunks(url, file)
    return output

def downloadChunks(url, file):
    try:
        req = urllib2.urlopen(url)
        total_size = int(req.info().getheader('Content-Length').strip())
        downloaded = 0
        CHUNK = 256 * 10240
        with open(file, 'wb') as fp:
            while True:
                chunk = req.read(CHUNK)
                downloaded += len(chunk)
                #print math.floor( (downloaded / total_size) * 100 )
                if not chunk: break
                fp.write(chunk)
    except urllib2.HTTPError, e:
        #print "HTTP Error:",e.code , url
        return False
    except urllib2.URLError, e:
        #print "URL Error:",e.reason , url
        return False

    return file

def copyFirstBoot(root):
    # Create the config plist
    config_plist = {}
    network = True
    retry_count = 10
    config_plist['Network'] = network
    config_plist['RetryCount'] = retry_count
    firstboot_dir = 'usr/local/first-boot'
    plistlib.writePlist(config_plist, os.path.join(root, firstboot_dir, 'config.plist'))

    # Copy the LaunchDaemon, LaunchAgent and LoginLog.app to the right places
    script_dir = os.path.dirname(os.path.realpath(__file__))
    NSLog(str(script_dir))
    launchDaemon_dir = os.path.join(root, 'Library', 'LaunchDaemons')
    if not os.path.exists(launchDaemon_dir):
        os.makedirs(launchDaemon_dir)
    shutil.copy(os.path.join(script_dir,
    'com.grahamgilbert.first-boot-pkg.plist'), os.path.join(launchDaemon_dir,
    'com.grahamgilbert.first-boot-pkg.plist'))
    # Set the permisisons
    os.chmod(os.path.join(launchDaemon_dir,
    'com.grahamgilbert.first-boot-pkg.plist'), 0644)
    os.chown(os.path.join(launchDaemon_dir,
    'com.grahamgilbert.first-boot-pkg.plist'), 0, 0)

    launchAgent_dir = os.path.join(root, 'Library', 'LaunchAgents')
    if not os.path.exists(launchAgent_dir):
        os.makedirs(launchAgent_dir)
    shutil.copy(os.path.join(script_dir, 'se.gu.it.LoginLog.plist'),
    os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'))
    # Set the permisisons
    os.chmod(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'), 0644)
    os.chown(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'), 0, 0)

    helperTools_dir = os.path.join(root, 'Library', 'PrivilegedHelperTools')
    if not os.path.exists(helperTools_dir):
        os.makedirs(helperTools_dir)
    shutil.copytree(os.path.join(script_dir, 'LoginLog.app'),
    os.path.join(helperTools_dir, 'LoginLog.app'))
    # Set the permisisons
    for root_dir, dirs, files in os.walk(os.path.join(helperTools_dir, 'LoginLog.app')):
      for momo in dirs:
        os.chown(os.path.join(root_dir, momo), 0, 0)
        os.chmod(os.path.join(root_dir, momo), 0755)
      for momo in files:
        os.chown(os.path.join(root_dir, momo), 0, 0)
        os.chmod(os.path.join(root_dir, momo), 0755)

    # copy the script
    shutil.copy(os.path.join(script_dir, 'first-boot'), os.path.join(root, firstboot_dir, 'first-boot'))
    # Set the permisisons
    os.chmod(os.path.join(root, firstboot_dir, 'first-boot'), 0755)
    os.chown(os.path.join(root, firstboot_dir, 'first-boot'), 0, 0)
