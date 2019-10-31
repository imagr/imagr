# -*- coding: utf-8 -*-
#
#  Utils.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

import hashlib
import os
import FoundationPlist
import plistlib
import shutil
import urllib
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import tempfile
import subprocess
import threading
import time
import sys
import xml.sax.saxutils
import logging
import urlparse
import socket
import urllib2
import datetime
import json
import macdisk
import objc

from gurl import Gurl


class GurlError(Exception):
    pass


class HTTPError(Exception):
    pass


class CustomThread(threading.Thread):
    '''Class for running a process in its own thread'''

    cmd = None

    def __init__(self, cmd=cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd


    def run(self):
        proc = subprocess.call(self.cmd)
        pass


diskutil_apfs_list_cache = []
diskutil_list_cache = []


def diskutil_list():
    global diskutil_list_cache
    if len(diskutil_list_cache)==0:
        cmd = ['/usr/sbin/diskutil', 'list', '-plist']
        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, unused_error) = proc.communicate()
        if proc.returncode:
            NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
            return volumes
        try:
            diskutil_list_cache = plistlib.readPlistFromString(output)
        except BaseException as e:
            NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))
    return diskutil_list_cache

def diskutil_apfs_list():
    global diskutil_apfs_list_cache
    if len(diskutil_apfs_list_cache)==0:
        cmd = ['/usr/sbin/diskutil', 'apfs','list', '-plist']
        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, unused_error) = proc.communicate()
        if proc.returncode:
            NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
            return ""
        try:
            diskutil_apfs_list_cache = plistlib.readPlistFromString(output)
        except BaseException as e:
            NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))

    return diskutil_apfs_list_cache

def header_dict_from_list(array):
    """Given a list of strings in http header format, return a dict.
    If array is None, return None"""
    if array is None:
        return array
    header_dict = {}
    for item in array:
        (key, sep, value) = item.partition(':')
        if sep and value:
            header_dict[key.strip()] = value.strip()
    return header_dict


def post_url(url, post_data, message=None, follow_redirects=False,
             progress_method=None, additional_headers=None):
    """Sends POST data to a URL and then returns the result.
    Accepts the URL to send the POST to, URL encoded data and
    optionally can follow redirects
    """
    temp_file = os.path.join(tempfile.mkdtemp(), 'tempdata')
    options = {'url': url,
               'file': temp_file,
               'follow_redirects': follow_redirects,
               'post_data': post_data,
               'additional_headers': header_dict_from_list(additional_headers),
               'logging_function': NSLog}

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
                # also display in progress field
                NSLog('%@', message)
                if progress_method:
                    progress_method(None, None, message)
                # now clear message so we don't display it again
                message = None
            if (str(connection.status).startswith('2')
                    and connection.percentComplete != -1):
                if connection.percentComplete != stored_percent_complete:
                    # display percent done if it has changed
                    stored_percent_complete = connection.percentComplete
                    NSLog('Percent done: %@', stored_percent_complete)
                    if progress_method:
                        progress_method(None, stored_percent_complete, None)
            elif connection.bytesReceived != stored_bytes_received:
                # if we don't have percent done info, log bytes received
                stored_bytes_received = connection.bytesReceived
                NSLog('Bytes received: %@', stored_bytes_received)
                if progress_method:
                    progress_method(None, None,
                                    'Bytes received: %s'
                                    % stored_bytes_received)
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

    if connection.error is not None:
        # Gurl returned an error
        if connection.SSLerror:
            NSLog('SSL error detail: %@', str(connection.SSLerror))
        NSLog('Headers: %@', str(connection.headers))
        raise GurlError(connection.error.code(),
                        connection.error.localizedDescription())

    if connection.response is not None:
        NSLog('Status: %@', connection.status)
        NSLog('Headers: %@', connection.headers)
    if connection.redirection != []:
        NSLog('Redirection: %@', connection.redirection)

    connection.headers['http_result_code'] = str(connection.status)
    description = NSHTTPURLResponse.localizedStringForStatusCode_(
        connection.status)
    connection.headers['http_result_description'] = description

    try:
        os.unlink(temp_file)
        os.rmdir(os.path.dirname(temp_file))
    except (OSError, IOError):
        pass
    if str(connection.status).startswith('2'):
        return connection.headers
    elif connection.status == 304:
        # unchanged on server
        NSLog('Item is unchanged on the server.')
        return connection.headers
    else:
        # there was an HTTP error of some sort
        raise HTTPError(connection.status,
                        connection.headers.get('http_result_description', ''))


def NSLogWrapper(message):
    '''A wrapper around NSLog so certain characters sent to NSLog don't '''
    '''trigger string substitution'''

def get_url(url, destinationpath, message=None, follow_redirects=False,
            progress_method=None, additional_headers=None, username=None,
            password=None, resume=False):
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
               'additional_headers': header_dict_from_list(additional_headers),
               'can_resume': resume,
               'username': username,
               'password': password,
               'logging_function': NSLogWrapper}

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
                # also display in progress field
                if progress_method:
                    progress_method(None, None, message)
                # now clear message so we don't display it again
                message = None
            if (str(connection.status).startswith('2')
                    and connection.percentComplete != -1):
                if connection.percentComplete != stored_percent_complete:
                    # display percent done if it has changed
                    stored_percent_complete = connection.percentComplete
                    NSLog('Percent done: %@', stored_percent_complete)
                    if progress_method:
                        progress_method(None, stored_percent_complete, None)
            elif connection.bytesReceived != stored_bytes_received:
                # if we don't have percent done info, log bytes received
                stored_bytes_received = connection.bytesReceived
                NSLog('Bytes received: %@', stored_bytes_received)
                if progress_method:
                    progress_method(None, None,
                                    'Bytes received: %s'
                                    % stored_bytes_received)
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

    if connection.error is not None:
        # Gurl returned an error
        if connection.SSLerror:
            NSLog('SSL error detail: %@', str(connection.SSLerror))
        if os.path.exists(tempdownloadpath):
            os.remove(tempdownloadpath)
        raise GurlError(connection.error.code(),
                        connection.error.localizedDescription())

    if connection.response is not None:
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
                        connection.headers.get('http_result_description', ''))


def downloadFile(url, additional_headers=None, username=None, password=None):
    url_parse = urlparse.urlparse(url)
    error = None
    error = type("err", (object,), dict())
    if url_parse.scheme in ['http', 'https']:
        # Use gurl to download the file
        temp_file = os.path.join(tempfile.mkdtemp(), 'tempdata')
        try:
            headers = get_url(
                url, temp_file, additional_headers=additional_headers,
                username=username, password=password)
        except HTTPError, err:
            NSLog("HTTP Error: %@", err)
            setattr(error, 'reason', err)
            data = False
        except GurlError, err:
            NSLog("Gurl Error: %@", err)
            setattr(error, 'reason', err)
            data = False
        try:
            file_handle = open(temp_file)
            data = file_handle.read()
            file_handle.close()
        except (OSError, IOError):
            NSLog('Couldn\'t read %@', temp_file)
            data = False
        try:
            os.unlink(temp_file)
            os.rmdir(os.path.dirname(temp_file))
        except (OSError, IOError):
            pass
    elif url_parse.scheme == 'file':
        # File resources should be handled natively
        try:
            data = urllib2.urlopen(url).read()
        except urllib2.URLError, err:
            setattr(error, 'reason', err)
            data = False
        except urllib2.HTTPError, err:
            setattr(error, 'reason', err)
            data = False

        # path = url.replace('file://','')
        # NSLog("%@", path)
        # try:
        #     file_handle = open(path)
        #     data = file_handle.read()
        #     file_handle.close()
        # except:
        #     setattr(error, 'reason', sys.exc_info()[0])
        #     data = False
    else:
        setattr(error, 'reason', 'The following URL is unsupported')
        data = False

    setattr(error, 'url', url)
    # Force universal newlines so Imagr can handle CRLF and CR file encoding.
    # This only affects script when they are embedded or file:/// resources.
    # https://docs.python.org/2/glossary.html#term-universal-newlines
    # if data is not False:
    #     data = '\n'.join(data.splitlines())
    return data, error


def getDMGSize(url):
    url_parse = urlparse.urlparse(url)
    error = None
    error = type("err", (object,), dict())
    if url_parse.scheme in ['http', 'https']:
        request = urllib2.Request(url)
        try:
            dmg = urllib2.urlopen(request)
            data = dmg.headers['Content-Length']
        except (urllib2.URLError, urllib2.HTTPError), err:
            setattr(error, 'reason', err)
            data = False
    else:
        setattr(error, 'reason', 'The following URL is unsupported')
        data = False

    setattr(error, 'url', url)
    return data, error


def getPasswordHash(password):
    return hashlib.sha512(password).hexdigest()

# Return the volume path of current working directory
def currentVolumePath():
    path = NSBundle.mainBundle().bundlePath()
    path = os.path.abspath(path)
    while not os.path.ismount(path):
       path = os.path.dirname(path)
    return path

def getPlistData(data):
    # Try the user's homedir
    try:
        # NSLog("Trying Home Location")
        homedir = os.path.expanduser("~")
        plist = FoundationPlist.readPlist(os.path.join(homedir, "Library", "Preferences", "com.grahamgilbert.Imagr.plist"))
        return plist[data]
    except:
        pass
    # Try the main prefs
    try:
        # NSLog("Trying System Location")
        plist = FoundationPlist.readPlist(os.path.join("/Library", "Preferences", "com.grahamgilbert.Imagr.plist"))
        return plist[data]
    except:
        pass

    # Hopefully we're in a netboot set, try in /System/Installation/Packages
    try:
        # NSLog("Trying NetBoot Location")
        plist = FoundationPlist.readPlist(os.path.join("/System", "Installation", "Packages", "com.grahamgilbert.Imagr.plist"))
        return plist[data]
    except:
        pass

    # last chance; look for a file next to the app
    appPath = NSBundle.mainBundle().bundlePath()
    appDirPath = os.path.dirname(appPath)
    try:
        plistData = open(os.path.join(appDirPath, "com.grahamgilbert.Imagr.plist")).read()
        plistData = plistData.replace("{{current_volume_path}}", currentVolumePath()).encode("utf8")
        plist = FoundationPlist.readPlistFromString(plistData)
        return plist[data]
    except:
        pass

def setDate():
    # Don't bother if we aren't running as root.
    if os.getuid() != 0:
        return

    def success():
        NSLog("Time successfully set to %@", datetime.datetime.now())

    def failure():
        NSLog("Failed to set time")

    # Try to set time with ntpdate.
    time_servers = [
        "time.apple.com",
        "pool.ntp.org",
    ]
    for server in time_servers:
        NSLog("Trying to set time with ntpdate from %@", server)
        try:
            subprocess.check_call(['/usr/sbin/ntpdate', '-su', server])
            success()
            return
        except OSError:
            # Couldn't execute ntpdate, go to plan B.
            break
        except subprocess.CalledProcessError:
            # Try next server.
            continue

    # ntpdate failed, so try making a HTTP request and then set the time from
    # the response header's Date field.
    date_data = None
    time_api_url = 'http://www.apple.com'

    try:
        request = urllib2.Request(time_api_url)
        request.get_method = lambda : 'HEAD'
        response = urllib2.urlopen(request, timeout=1)
        date_data = response.info().getheader('Date')
    except:
        pass

    if date_data:
        try:
            timestamp = datetime.datetime.strptime(date_data, '%a, %d %b %Y %H:%M:%S GMT')
            # date {month}{day}{hour}{minute}{year}
            formatted_date = datetime.datetime.strftime(timestamp, '%m%d%H%M%y')

            _ = subprocess.Popen(['/bin/date', formatted_date], env={'TZ': 'GMT'}).communicate()
            return
        except:
            pass

    failure()


def getServerURL():
    data = getPlistData('serverurl')
    return data


def getReportURL():
    report_url = getPlistData('reporturl')
    if report_url:
        return report_url
    else:
        return None


def sendReport(status, message):
    hardware_info = get_hardware_info()
    SERIAL = hardware_info.get('serial_number', 'UNKNOWN')

    report_url = getReportURL()
    curr_hostname = hostname()
    if report_url and len(message) > 0:
        # Should probably do some validation on the status at some point
        data = {
            'hostname':curr_hostname,
            'status': status,
            'serial': SERIAL,
            'message': message
        }
        data = urllib.urlencode(data)
        # silently fail here, sending reports is a nice to have, if server is
        # down, meh.
        try:
            post_url(report_url, data)
        except:
            pass

    if len(message) > 0:
        log_message = "[{}] {}".format(SERIAL, message)
        log = logging.getLogger("Imagr")
        NSLog(log_message)
        
        if status == 'error':
            log.error(log_message)
        else:
            log.info(log_message)


def bringToFront(bundleID):
    startTime = time.time()
    while time.time() - startTime < 10:
        for runapp in NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundleID):
            runapp.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            if runapp.isActive():
                return
        time.sleep(1/10.0)


def launchApp(app_path):
    # Get the binary path so we can launch it using a threaded subprocess
    try:
        app_plist = FoundationPlist.readPlist(os.path.join(app_path, 'Contents', 'Info.plist'))
        binary = app_plist['CFBundleExecutable']
    except:
        NSLog("Failed to get app binary location, cannot launch.")
        return

    if not NSRunningApplication.runningApplicationsWithBundleIdentifier_(app_plist['CFBundleIdentifier']):
        # Only launch the app if it isn't already running
        thread = CustomThread(os.path.join(app_path, 'Contents', 'MacOS',
                                           binary))
        thread.daemon = True
        thread.start()

    # Bring application to the front as they launch in the background in
    # Netboot for some reason
    bringToFront(app_plist['CFBundleIdentifier'])


def get_hardware_info():

    """
    system_profiler is not included in a 10.13 NetInstall NBI, therefore a new method of getting serial numer and model identifier is required
    Thanks to frogor's work on how to access IOKit from python: https://gist.github.com/pudquick/c7dd1262bd81a32663f0
    """

    IOKit_bundle = NSBundle.bundleWithIdentifier_('com.apple.framework.IOKit')

    functions = [("IOServiceGetMatchingService", b"II@"),
                 ("IOServiceMatching", b"@*"),
                 ("IORegistryEntryCreateCFProperty", b"@I@@I"),
                ]

    objc.loadBundleFunctions(IOKit_bundle, globals(), functions)

    def io_key(keyname):
        return IORegistryEntryCreateCFProperty(IOServiceGetMatchingService(0, IOServiceMatching("IOPlatformExpertDevice")), keyname, None, 0)

    hardware_info_plist = {}
    hardware_info_plist['serial_number'] = io_key("IOPlatformSerialNumber")
    hardware_info_plist['machine_model'] = str(io_key("model")).rstrip('\x00')

    return hardware_info_plist


def setup_logging():
    syslog = getPlistData('syslog')

    if not syslog:
        return

    # Parse syslog URI
    try:
        uri = urlparse.urlparse(syslog)
        qs = urlparse.parse_qs(uri.query)

        hostname = uri.hostname if uri.hostname else "localhost"
        port = uri.port if uri.port else 514
        socktype = socket.SOCK_STREAM if qs['transport'][0] == 'TCP' else socket.SOCK_DGRAM
        facility = qs['facility'][0] if 'facility' in qs else "local7"
    except:
        NSLog("Failed to parse syslog URI.")

    # Create a syslog handler
    handler = logging.handlers.SysLogHandler(address=(hostname, port),
                                             facility=facility,
                                             socktype=socktype)

    # Configure logging
    formatter = logging.Formatter('%(name)s: %(message)s')
    handler.setFormatter(formatter)
    logging.getLogger("Imagr").addHandler(handler)
    logging.getLogger("Imagr").setLevel("INFO")


def replacePlaceholders(script, target, computer_name=None,
                        keyboard_layout_id=None, keyboard_layout_name=None,
                        language=None, locale=None, timezone=None):
    hardware_info = get_hardware_info()
    placeholders = {
        "{{target_volume}}": target,
        "{{serial_number}}": hardware_info.get('serial_number', 'UNKNOWN'),
        "{{machine_model}}": hardware_info.get('machine_model', 'UNKNOWN'),
    }

    if computer_name:
        placeholders['{{computer_name}}'] = computer_name

    if isinstance(keyboard_layout_id, int):
        placeholders['{{keyboard_layout_id}}'] = keyboard_layout_id

    if keyboard_layout_name:
        placeholders['{{keyboard_layout_name}}'] = keyboard_layout_name

    if language:
        placeholders['{{language}}'] = language

    if locale:
        placeholders['{{locale}}'] = locale

    if timezone:
        placeholders['{{timezone}}'] = timezone

    for placeholder, value in placeholders.iteritems():
        script = script.replace(placeholder, str(value))

    script = xml.sax.saxutils.unescape(script)
    return script


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
        if retcode:
            print >> sys.stderr, 'Failed to unmount %s' % mountpoint
            return False
        else:
            return True
    else:
        return True


def downloadChunks(url, file, progress_method=None, additional_headers=None, resume=False):
    message = "Downloading %s" % os.path.basename(url)
    url_parse = urlparse.urlparse(url)
    if url_parse.scheme in ['http', 'https']:
        # Use gurl to download the file
        try:
            headers = get_url(url, file, message=message, resume=resume,
                              progress_method=progress_method,
                              additional_headers=additional_headers)
            return file, None
        except HTTPError, error:
            NSLog("HTTP Error: %@", error)
            return False, error
        except GurlError, error:
            NSLog("Gurl Error: %@", error)
            return False, error
    elif url_parse.scheme == 'file':
        # File resources should be handled natively. Space characters, %20,
        # need to be removed
        # for /usr/sbin/installer and shutil.copy to function properly.
        source = url_parse.path.replace("%20", " ")
        try:
            if os.path.isfile(source):
                shutil.copy(source, file)
            else:
                shutil.copytree(source, file)
            return source, None
        except:
            error = "Unable to copy %s" % url
            return False, error
    else:
        # Garbage in garbage out. We don't know what to do with this type of
        # url.
        error = "Cannot handle url scheme: '%s' from %s" % (url_parse.scheme,
                                                            url)
        return False, error


def copyFirstBoot(root, network=True, reboot=True):
    NSLog("Copying first boot pkg install tools")
    # Create the config plist
    config_plist = {}
    retry_count = 10
    config_plist['Network'] = network
    config_plist['RetryCount'] = retry_count
    config_plist['Reboot'] = reboot
    firstboot_dir = 'private/var/.imagr/first-boot'
    if not os.path.exists(os.path.join(root, firstboot_dir)):
        os.makedirs(os.path.join(root, firstboot_dir))
    plistlib.writePlist(config_plist, os.path.join(root, firstboot_dir,
                                                   'config.plist'))

    # Copy the LaunchDaemon, LaunchAgent and Log.app to the right places
    script_dir = os.path.dirname(os.path.realpath(__file__))
    launchDaemon_dir = os.path.join(root, 'Library', 'LaunchDaemons')
    if not os.path.exists(launchDaemon_dir):
        os.makedirs(launchDaemon_dir, 0755)
        os.chown(launchDaemon_dir, 0, 0)

    if not os.path.exists(os.path.join(launchDaemon_dir,
    'com.grahamgilbert.imagr-first-boot-pkg.plist')):
        shutil.copy(os.path.join(script_dir,
        'com.grahamgilbert.imagr-first-boot-pkg.plist'), os.path.join(launchDaemon_dir,
        'com.grahamgilbert.imagr-first-boot-pkg.plist'))
        # Set the permisisons
        os.chmod(os.path.join(launchDaemon_dir,
        'com.grahamgilbert.imagr-first-boot-pkg.plist'), 0644)
        os.chown(os.path.join(launchDaemon_dir,
        'com.grahamgilbert.imagr-first-boot-pkg.plist'), 0, 0)

    launchAgent_dir = os.path.join(root, 'Library', 'LaunchAgents')
    if not os.path.exists(launchAgent_dir):
        os.makedirs(launchAgent_dir, 0755)
        os.chown(launchAgent_dir, 0, 0)

    if not os.path.exists(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist')):
        shutil.copy(os.path.join(script_dir, 'se.gu.it.LoginLog.plist'),
        os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'))
        # Set the permisisons
        os.chmod(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'), 0644)
        os.chown(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.plist'), 0, 0)

    if not os.path.exists(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.login.plist')):
        shutil.copy(os.path.join(script_dir, 'se.gu.it.LoginLog.login.plist'),
        os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.login.plist'))
        # Set the permisisons
        os.chmod(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.login.plist'), 0644)
        os.chown(os.path.join(launchAgent_dir, 'se.gu.it.LoginLog.login.plist'), 0, 0)

    helperTools_dir = os.path.join(root, 'Library', 'PrivilegedHelperTools')
    if not os.path.exists(helperTools_dir):
        os.makedirs(helperTools_dir, 0755)
        os.chown(helperTools_dir, 0, 0)

    if not os.path.exists(os.path.join(helperTools_dir, 'LoginLog.app')):
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

    if not os.path.exists(os.path.join(root, firstboot_dir, 'first-boot')):
        # copy the script
        shutil.copy(os.path.join(script_dir, 'first-boot'), os.path.join(root, firstboot_dir, 'first-boot'))
        # Set the permisisons
        os.chmod(os.path.join(root, firstboot_dir, 'first-boot'), 0755)
        os.chown(os.path.join(root, firstboot_dir, 'first-boot'), 0, 0)


def is_apfs(source):
    """
    Returns true if source image is AFPS
    """
    isApfs = False
    cmd = ['/usr/bin/hdiutil', 'imageinfo', '-plist', source]
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
        return isApfs
    try:
        plist = plistlib.readPlistFromString(output)
        if 'partitions' in plist:
            for partition in plist['partitions'].iteritems():

                if partition[0] == 'partitions':
                    for item in partition[1]:
                        hint = item.get('partition-hint', '')
                        if hint == 'Apple_APFS':
                            isApfs = True

    except Exception as e:
        NSLog(u"Failed to get disk image format %@", str(e))
        return isApfs
    return isApfs

def mountedVolumes():
    """Return an array with information dictionaries for each mounted volume."""
    volumes = []
    plist =  diskutil_list()
    volumeNames = plist[u"VolumesFromDisks"]
    for disk in plist[u"AllDisksAndPartitions"]:
        if (u"MountPoint" in disk) and (not disk[u"MountPoint"].startswith("/private/var")) and (disk.get(u"VolumeName") in volumeNames):
            volumes.append(macdisk.Disk(disk[u"DeviceIdentifier"]))
        for part in disk.get(u"Partitions", []):
            if ((u"MountPoint" in part) and (not part[u"MountPoint"].startswith("/private/var")) and (part.get(u"VolumeName") in volumeNames)) :
                volumes.append(macdisk.Disk(part[u"DeviceIdentifier"]))

#         volumes = [disk for disk in volumes if not disk.mountpoint in APFSVolumesToHide]
#         print volumes


    
    return volumes

def mounted_apfs_volumes():
    volumes = []
    plist = diskutil_list()
    volumeNames = plist[u"VolumesFromDisks"]
    for disk in plist[u"AllDisksAndPartitions"]:
        for part in disk.get(u"APFSVolumes", []):
            if (u"MountPoint" in part) and (not part[u"MountPoint"].startswith("/private/var")) and (part.get(u"VolumeName") in volumeNames) :
                    volumes.append(part[u"DeviceIdentifier"])

    return volumes

def data_volume(source) :

    newDisk=source
    if (source._attributes['FilesystemType'] == 'apfs'):
        container_reference=source._attributes['ParentWholeDisk']
        plist = diskutil_apfs_list()

        if (plist==""):
            return newDisk
        for container in plist[u"Containers"]:
            if (container[u"ContainerReference"]!=container_reference):
                continue
            for volume in container[u"Volumes"]:
                if ((u"Roles" in volume) and (u"Data" in volume["Roles"])):
                    newDisk=macdisk.Disk(volume[u"DeviceIdentifier"])
                    newDisk.Refresh()
    return newDisk

def system_volume(source):
    newDisk=source
    if (source._attributes['FilesystemType'] == 'apfs'):
        container_reference=source._attributes['ParentWholeDisk']
        plist = diskutil_apfs_list()

        if (plist==""):
            return newDisk
        for container in plist[u"Containers"]:
            if (container[u"ContainerReference"]!=container_reference):
                continue
            for volume in container[u"Volumes"]:
                if ((u"Roles" in volume) and (u"System" in volume["Roles"])):
                    newDisk=macdisk.Disk(volume[u"DeviceIdentifier"])
                    newDisk.Refresh()
    return newDisk


def hostname():
    hostname="Unknown"
    cmd = ['/bin/hostname','-s']
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (hostname, unused_error) = proc.communicate()

    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
        return hostname

    return hostname.rstrip('\r\n')


def available_volumes():
    global diskutil_list_cache
    global diskutil_apfs_list_cache

    diskutil_list_cache=[]
    diskutil_apfs_list_cache=[]
    volumes=available_apfs_volumes()
    volumes.extend(cs_filevault_volumes())
    volumes.extend(mountedVolumes())
    return volumes

def available_apfs_volumes():

    volumes = []
    plist = diskutil_apfs_list()
    if (plist==""):
        return volumes
    mount_vols=mounted_apfs_volumes()
    for container in plist[u"Containers"]:
        for volume in container[u"Volumes"]:
            if ((u"FileVault" in volume) and (volume["FileVault"]==True) or (volume[u"DeviceIdentifier"] in mount_vols and (u"Roles" in volume) and (not u"Data" in volume["Roles"]))):
                newDisk=macdisk.Disk(volume[u"DeviceIdentifier"])
                if (u"FileVault" in volume) and (volume["FileVault"]==True):
                    newDisk.filevault=True
                newDisk.Refresh()
                volumes.append(newDisk)

    return volumes
def apfs_filevault_volumes():

    volumes = []
    plist = diskutil_apfs_list()

    if (plist==""):
        volumes
    for container in plist[u"Containers"]:
        for volume in container[u"Volumes"]:
            if (u"FileVault" in volume) and (volume["FileVault"]==True):
                newDisk=macdisk.Disk(volume[u"DeviceIdentifier"])
                newDisk.filevault=True
                newDisk.Refresh()
                volumes.append(newDisk)
    return volumes

def apfs_volume_uuid(device):
    cmd = ['/usr/sbin/diskutil', 'info','-plist',device]
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
        return volumes

    try:
        plist = plistlib.readPlistFromString(output)
    except BaseException as e:
        NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))

    return plist[u'VolumeUUID']


def apfs_container(volume_uuid):
    plist = diskutil_apfs_list()

    if (plist==""):
        return ""
    for container in plist[u"Containers"]:
        for volume in container[u"Volumes"]:
            if volume[u"APFSVolumeUUID"]==volume_uuid:
                return container[u"APFSContainerUUID"]

def first_apfs_volume(apfs_container_uuid):
    ret_disk=None
    plist=diskutil_apfs_list()

    if (plist==""):
        return None
    try:
        new_device=plist[u"Containers"][0][u"Volumes"][0][u"DeviceIdentifier"]
        ret_disk=macdisk.Disk(new_device)
    except BaseException as e:
        NSLog(u"Couldn't get new device from %@",apfs_container_uuid)

    return ret_disk


def reset_apfs_container(device,new_volume_name=u"Macintosh HD"):

    apfs_vol_uuid=apfs_volume_uuid(device)
    apfs_container_uuid=apfs_container(apfs_vol_uuid)
    first_vol=None

    if apfs_container_uuid:
        cmd = ['/usr/sbin/diskutil', 'apfs', 'list','-plist',apfs_container_uuid]
        proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, unused_error) = proc.communicate()
        if proc.returncode:
            NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
            

        try:
            plist = plistlib.readPlistFromString(output)
        except BaseException as e:
            NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))
        
        NSLog(u"deleting volumes");
        for container in plist[u"Containers"]:
            for volume in container[u"Volumes"]:
                apfs_delete_volume(volume[u"APFSVolumeUUID"])

        NSLog(u"adding volume named %@ to container UUID %@", new_volume_name,apfs_container_uuid)
        apfs_add_volume(apfs_container_uuid, new_volume_name)
        NSLog(u"finding first volume in container %@",apfs_container_uuid)
        diskutil_list_cache=""
        diskutil_apfs_list=""
        first_vol=first_apfs_volume(apfs_container_uuid)

    return first_vol

        


def apfs_add_volume(apfs_container_uuid,new_name):

    cmd = ['/usr/sbin/diskutil', 'apfs', 'addVolume',apfs_container_uuid,"apfs",new_name]
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)


def apfs_delete_volume(apfs_volume_uuid):

    cmd = ['/usr/sbin/diskutil', 'apfs', 'deleteVolume',apfs_volume_uuid]
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)

def cs_filevault_volumes():

    volumes = []
    cmd = ['/usr/sbin/diskutil', 'cs', 'list','-plist']
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
        return volumes
    try:
        plist = plistlib.readPlistFromString(output)
    except BaseException as e:
        NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))

    if "CoreStorageLogicalVolumeGroups" in plist:
        for logicalVolumeGroup in plist[u"CoreStorageLogicalVolumeGroups"]:
            for logicalVolumeFamily in logicalVolumeGroup[u"CoreStorageLogicalVolumeFamilies"]:
                for logicalVolume in logicalVolumeFamily[u"CoreStorageLogicalVolumes"]:
                    coreStorageUUID=logicalVolume["CoreStorageUUID"]
                    logicalVolumeInfo=cs_volume_info(coreStorageUUID)
                    if (logicalVolumeInfo["CoreStorageLogicalVolumeStatus"]=='Locked'):
                        newDisk=macdisk.Disk(logicalVolumeInfo[u"DesignatedCoreStoragePhysicalVolumeDeviceIdentifier"])
                        newDisk.filevault=True
                        newDisk.Refresh()
                        volumes.append(newDisk)
                    else:
                        NSLog("Not locked")

    return volumes





def cs_volume_info(cs_disk_id):

    cmd = ['/usr/sbin/diskutil', 'cs', 'info','-plist',cs_disk_id]
    proc = subprocess.Popen(cmd, shell=False, bufsize=-1,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (output, unused_error) = proc.communicate()
    if proc.returncode:
        NSLog(u"%@ failed with return code %d", u" ".join(cmd), proc.returncode)
        return volumes

    try:
        plist = plistlib.readPlistFromString(output)
    except BaseException as e:
        NSLog(u"Couldn't parse output from %@: %@", u" ".join(cmd), unicode(e))

    return plist
