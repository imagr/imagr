# -*- coding: utf-8 -*-
#
#  Utils.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

#import urllib2
import hashlib
import os
import FoundationPlist
#import math
import plistlib
import shutil
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import tempfile
import subprocess

from gurl import Gurl

class GurlError(Exception):
    pass

class HTTPError(Exception):
    pass

def get_url(url, destinationpath, message=None, follow_redirects=False):
    """Gets an HTTP or HTTPS URL and stores it in
    destination path. Returns a dictionary of headers, which includes
    http_result_code and http_result_description.
    Will raise GurlError if Gurl returns an error.
    Will raise HTTPError if HTTP Result code is not 2xx or 304.
    If destinationpath already exists, you can set 'onlyifnewer' to true to
    indicate you only want to download the file only if it's newer on the
    server.
    If you set resume to True, Gurl will attempt to resume an
    interrupted download."""

    tempdownloadpath = destinationpath + '.download'
    if os.path.exists(tempdownloadpath):
        os.remove(tempdownloadpath)

    options = {'url': url,
               'file': tempdownloadpath,
               'follow_redirects': follow_redirects,
               'logging_function': NSLog}
    NSLog('gurl options: %@',  options)

    connection = Gurl.alloc().initWithOptions_(options)
    stored_percent_complete = -1
    stored_bytes_received = 0
    connection.start()
    try:
        while True:
            # if we did `while not connection.isDone()` we'd miss printing
            # messages and displaying percentages if we exit the loop first
            connection_done = connection.isDone()
            if message and connection.status and connection.status != 304:
                # log always, display if verbose is 1 or more
                # also display in MunkiStatus detail field
                NSLog(message)
                # now clear message so we don't display it again
                message = None
            if (str(connection.status).startswith('2')
                and connection.percentComplete != -1):
                if connection.percentComplete != stored_percent_complete:
                    # display percent done if it has changed
                    stored_percent_complete = connection.percentComplete
                    NSLog('Percent done: %@', stored_percent_complete)
            elif connection.bytesReceived != stored_bytes_received:
                # if we don't have percent done info, log bytes received
                stored_bytes_received = connection.bytesReceived
                NSLog('Bytes received: %@', stored_bytes_received)
            if connection_done:
                break

    except (KeyboardInterrupt, SystemExit):
        # safely kill the connection then re-raise
        connection.cancel()
        raise
    except Exception, err: # too general, I know
        # Let us out! ... Safely! Unexpectedly quit dialogs are annoying...
        connection.cancel()
        # Re-raise the error as a GurlError
        raise GurlError(-1, str(err))

    if connection.error != None:
        # Gurl returned an error
        NSLog('Download error %@: %@', connection.error.code(),
              connection.error.localizedDescription())
        if connection.SSLerror:
           NSLog('SSL error detail: %@', str(connection.SSLerror))
        NSLog('Headers: %@', str(connection.headers))
        if os.path.exists(tempdownloadpath):
            os.remove(tempdownloadpath)
        raise GurlError(connection.error.code(), 
                        connection.error.localizedDescription())

    if connection.response != None:
        NSLog('Status: %@', connection.status)
        NSLog('Headers: %@', connection.headers)
    if connection.redirection != []:
        NSLog('Redirection: %@', connection.redirection)

    temp_download_exists = os.path.isfile(tempdownloadpath)
    connection.headers['http_result_code'] = str(connection.status)
    description = NSHTTPURLResponse.localizedStringForStatusCode_(
                                                            connection.status)
    connection.headers['http_result_description'] = description

    if str(connection.status).startswith('2') and temp_download_exists:
        os.rename(tempdownloadpath, destinationpath)
        return connection.headers
    elif connection.status == 304:
        # unchanged on server
        NSLog('Item is unchanged on the server.')
        return connection.headers
    else:
        # there was an HTTP error of some sort; remove our temp download.
        if os.path.exists(tempdownloadpath):
            try:
                os.unlink(tempdownloadpath)
            except OSError:
                pass
        raise HTTPError(connection.status,
                        connection.headers.get('http_result_description',''))

def downloadFile(url):
    temp_file = os.path.expanduser('~/Library/temporary_data')
    try:
        headers = get_url(url, temp_file)
    except HTTPError, err:
        NSLog("HTTP Error: %@", err)
        return False
    except GurlError, err:
        NSLog("Gurl Error: %@", err)
        return False
    try:
        file_handle = open(temp_file)
        data = file_handle.read()
        file_handle.close()
    except (OSError, IOError):
        NSLog('Couldn\'t read %@', temp_file)
        return False
    try:
        os.unlink(temp_file)
    except (OSError, IOError):
        pass
    return data


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


def downloadAndInstallPackage(url, target, number, package_count):
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
    NSLog("Installing %@ to %@", pkg, target)
    installer_pool = NSAutoreleasePool.alloc().init()
    cmd = ['/usr/sbin/installer', '-pkg', pkg, '-target', target]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unusederr) = proc.communicate()
    if unusederr:
        NSLog(str(unusederr))


def mountdmg(dmgpath):
    """
    Attempts to mount the dmg at dmgpath
    and returns a list of mountpoints
    """
    NSLog("Mounting disk image %@", dmgpath)
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
    NSLog("Unmounting disk image at %@", mountpoint)
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


def copyPkgFromDmg(url, dest_dir, number):
    # We're going to mount the dmg
    dmgmountpoints = mountdmg(url)
    dmgmountpoint = dmgmountpoints[0]

    # Now we're going to go over everything that ends .pkg or
    # .mpkg and install it
    pkg_list = []
    for package in os.listdir(dmgmountpoint):
        if package.endswith('.pkg') or package.endswith('.mpkg'):
            pkg = os.path.join(dmgmountpoint, package)
            dest_file = os.path.join(dest_dir, "%03d-%s" % (number, os.path.basename(pkg)))
            if os.path.isfile(pkg):
                shutil.copy(pkg, dest_file)
            else:
                shutil.copytree(pkg, dest_file)
            pkg_list.append(dest_file)

    # Unmount it
    unmountdmg(dmgmountpoint)

    if not pkg_list:
        NSLog("No packages found in %@", url)
        result = False
    else:
        result = pkg_list

    return result


def downloadPackage(url, target, number, package_count):
    dest_dir = os.path.join(target, 'usr/local/first-boot/packages')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    if os.path.basename(url).endswith('.dmg'):
        NSLog("Copying pkg(s) from %@", url)
        output = copyPkgFromDmg(url, dest_dir, number)
    else:
        NSLog("Downloading pkg %@", url)
        package_name = "%03d-%s" % (number, os.path.basename(url))
        os.umask(0002)
        file = os.path.join(dest_dir, package_name)
        output = downloadChunks(url, file)

    return output


def downloadChunks(url, file):
    try:
        headers = get_url(url, file)
    except HTTPError, err:
        NSLog("HTTP Error: %@", err)
        return False
    except GurlError, err:
        NSLog("Gurl Error: %@", err)
        return False
    else:
        return file


def copyFirstBoot(root):
    NSLog("Copying first boot pkg install tools")
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
