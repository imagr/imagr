# encoding: utf-8
#
# Copyright 2017 Greg Neagle.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
osinstall.py

Created by Greg Neagle on 2017-10-09.

Support for using startosinstall to install macOS.
"""

# stdlib imports
import os
import shutil
import subprocess
from distutils import version

# PyObjC bindings
from Foundation import NSLog

# our imports
import FoundationPlist
import Utils


def find_install_macos_app(dir_path):
    '''Returns the path to the first Install macOS.app found the top level of
    dir_path, or None'''
    for item in os.listdir(dir_path):
        item_path = os.path.join(dir_path, item)
        startosinstall_path = os.path.join(
            item_path, 'Contents/Resources/startosinstall')
        if os.path.exists(startosinstall_path):
            return item_path
    # if we get here we didn't find one
    return None


def install_macos_app_is_stub(app_path):
    '''High Sierra downloaded installer is sometimes a "stub" application that
    does not contain the InstallESD.dmg. Retune True if the given app path is
    missing the InstallESD.dmg'''
    installesd_dmg = os.path.join(
        app_path, 'Contents/SharedSupport/InstallESD.dmg')
    return not os.path.exists(installesd_dmg)


def get_os_version(app_path):
    '''Returns the os version from the OS Installer app'''
    installinfo_plist = os.path.join(
        app_path, 'Contents/SharedSupport/InstallInfo.plist')
    if not os.path.isfile(installinfo_plist):
        # no Contents/SharedSupport/InstallInfo.plist
        return ''
    try:
        info = FoundationPlist.readPlist(installinfo_plist)
        return info['System Image Info']['version']
    except (FoundationPlist.FoundationPlistException,
            IOError, KeyError, AttributeError, TypeError):
        return ''


class PkgCachingError(Exception):
    '''Error to return if we have a problem caching a pkg for startosinstall'''
    pass


def cache_pkg(url, dest_dir, progress_method=None):
    '''Download and cache a package'''
    error = None
    package_name = os.path.basename(url)
    os.umask(0002)
    pkgpath = os.path.join(dest_dir, package_name)
    (_, error) = Utils.downloadChunks(
        url, pkgpath, progress_method=progress_method)
    if error:
        raise PkgCachingError(
            'Error downloading %s - %s' % (url, error))
    return pkgpath


def cache_pkg_from_dmg(url, dest_dir):
    '''Download and cache a package wrapped in a dmg'''
    # We're going to mount the dmg
    try:
        dmgmountpoints = Utils.mountdmg(url)
        dmgmountpoint = dmgmountpoints[0]
    except:
        raise PkgCachingError('Couldn\'t mount %s' % url)

    # Cache the first pkg found on the dmg
    pkg_list = [item for item in os.listdir(dmgmountpoint)
                if item.endswith(('.pkg', '.mpkg'))]
    if len(pkg_list) == 0:
        raise PkgCachingError('No packages found on %s' % url)
    if len(pkg_list) > 1:
        raise PkgCachingError('More than one package found on %s' % url)

    pkg = pkg_list[0]
    source_file = os.path.join(dmgmountpoint, pkg)
    if not os.path.isfile(source_file):
        raise PkgCachingError(
            'Non-flat package %s found on %s' % (pkg, url))

    dest_file = os.path.join(dest_dir, pkg)
    try:
        shutil.copy(source_file, dest_file)
    except Exception, err:
        raise PkgCachingError('Couldn\'t copy %s: %s' % (pkg, unicode(err)))

    # Unmount it
    try:
        Utils.unmountdmg(dmgmountpoint)
    except:
        raise PkgCachingError('Couldn\'t unmount %s' % dmgmountpoint)

    return dest_file


def download_and_cache_pkgs(pkgurls, target, progress_method=None):
    '''Given a list of urls to packages, download the pkgs and stash them
    on the target volume. Return a list of the stashed paths.
    Raise PkgCaching error if there is a problem'''
    pkgpaths = []
    dest_dir = os.path.join(target, 'private/tmp/pkgcache')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    for url in pkgurls:
        if (not os.path.basename(url).endswith('.pkg') and
                not os.path.basename(url).endswith('.dmg')):
            error = "%s doesn't end with either '.pkg' or '.dmg'" % url
            raise PkgCachingError(error)
        NSLog("Caching pkg from %@", url)
        if os.path.basename(url).endswith('.dmg'):
            pkgpath = cache_pkg_from_dmg(url, dest_dir)
        else:
            pkgpath = cache_pkg(url, dest_dir, progress_method=progress_method)
        pkgpaths.append(pkgpath)

    return pkgpaths


def run(item, target, progress_method=None):
    '''Run startosinstall from Install macOS app on a disk image'''
    url = item.get('url')
    # url better point to a disk image containing the Install macOS app
    try:
        dmgmountpoints = Utils.mountdmg(url)
        dmgmountpoint = dmgmountpoints[0]
    except:
        error_message = "Couldn't mount disk image from %s" % url
        return False, error_message

    app_path = find_install_macos_app(dmgmountpoint)
    startosinstall_path = os.path.join(
        app_path, 'Contents/Resources/startosinstall')
    installed_os_version = get_os_version(app_path)

    additional_package_paths = []
    if (version.LooseVersion(
            installed_os_version) >= version.LooseVersion('10.13') and
            'additional_package_urls' in item):
        try:
            additional_package_paths = download_and_cache_pkgs(
                item['additional_package_urls'], target,
                progress_method=progress_method)
        except PkgCachingError, err:
            return False, unicode(err)

    # we need to wrap our call to startosinstall with a utility
    # that makes startosinstall think it is connected to a tty-like
    # device so its output is unbuffered so we can get progress info
    # otherwise we get nothing until the process exits.
    #
    # Try to find our ptyexec tool
    # first look in the this file's enclosing directory
    # (../)
    this_dir = os.path.dirname(os.path.abspath(__file__))
    ptyexec_path = os.path.join(this_dir, 'ptyexec')
    if os.path.exists(ptyexec_path):
        cmd = [ptyexec_path]
    else:
        # fall back to /usr/bin/script
        # this is not preferred because it uses way too much CPU
        # checking stdin for input that will never come...
        cmd = ['/usr/bin/script', '-q', '-t', '1', '/dev/null']

    cmd.extend([startosinstall_path,
                '--agreetolicense',
                '--applicationpath', app_path,
                '--volume', target,
                '--nointeraction'])

    # add additional startosinstall options if any
    if 'additional_startosinstall_options' in item:
        cmd.extend(item['additional_startosinstall_options'])

    # add additional pkgs to install if any
    for pkg in additional_package_paths:
        cmd.extend(['--installpackage', pkg])

    NSLog('startosinstall cmd: %@', cmd)

    # more magic to get startosinstall to not buffer its output for
    # percent complete
    env = {'NSUnbufferedIO': 'YES'}

    proc = subprocess.Popen(
        cmd, shell=False, bufsize=-1, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    startosinstall_output = []
    while True:
        output = proc.stdout.readline()
        if not output and (proc.returncode != None):
            break
        info_output = output.rstrip('\n').decode('UTF-8')
        # save all startosinstall output in case there is
        # an error so we can dump it to the log
        startosinstall_output.append(info_output)

        # parse output for useful progress info
        msg = info_output.rstrip('\n')
        if msg.startswith('Preparing to '):
            NSLog('%@', msg)
            if progress_method:
                progress_method(None, None, msg)
        elif msg.startswith('Preparing '):
            # percent-complete messages
            try:
                percent = int(float(msg[10:].rstrip().rstrip('.')))
            except ValueError:
                percent = -1
            if progress_method:
                progress_method(None, percent, None)
        elif msg.startswith(('By using the agreetolicense option',
                             'If you do not agree,')):
            # annoying legalese
            pass
        elif msg.startswith('Helper tool cr'):
            # no need to print that stupid message to screen!
            # 10.12: 'Helper tool creashed'
            # 10.13: 'Helper tool crashed'
            NSLog('%@', msg)
        elif msg.startswith(
                ('Signaling PID:', 'Waiting to reboot',
                 'Process signaled okay')):
            # messages around the SIGUSR1 signalling
            NSLog('%@', msg)
        elif msg.startswith('System going down for install'):
            msg = 'System will restart and begin install of macOS.'
            NSLog('%@', msg)
            if progress_method:
                progress_method(None, None, msg)
        else:
            # none of the above, just display
            NSLog('%@', msg)
            if progress_method:
                progress_method(None, None, msg)

    return_code = proc.returncode
    errors = proc.stderr.read()
    if return_code != 0:
        NSLog('##### startosinstall stderr: #####')
        NSLog('%@', errors)
        return False, 'startosinstall failed with return code %s' % return_code
    else:
        return True, 'OK'
