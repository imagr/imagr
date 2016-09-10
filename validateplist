#!/usr/bin/python

"""
This script will validate an Imagr configuration plist. Usage:
./validateplist ~/path/to/config.plist

    The rules of Imagr
    #1 - if there is a password, its hash must not be empty
    #2 - there must be at least one workflow
    #3 - Workflow names must be unique
    #4 - Image components must have a url
    #5 - Image urls must end in dmg
    #6 - Package components must have a url
    #7 - Package urls must end with either pkg or dmg
    #8 - Scripts must have content or a url
    #9 - Restart actions must be 'none', 'shutdown' or 'restart'
    #10 - first_boot must be a boolean on all component types
    #11 - Partition actions must have at least one partition
    #12 - Partition actions must have a target
    #13 - Partition actions must have one 'size' for each partition, if 'size' is specified
    #14 - Partition actions must not be done at first boot
    #15 - eraseVolume actions must not be done at first boot
    #16 - if a default workflow is specified, it must match the name of an existing workflow
    #17 - if a workflow to autorun is specified, it must match the name of an existing workflow
    #18 - If a destructive task comes after a non-destructive task, the admin should be warned
    #19 - If image components have a verify option it must be a bool
    #20 - Background images should have a valid url
"""

import os
import sys
import argparse
import plistlib
import subprocess
import tempfile
import shutil
import urlparse
import urllib2
if os.path.exists(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Imagr')):
    sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Imagr'))
elif os.path.exists('/usr/local/munki/munkilib'):
    sys.path.append('/usr/local/munki/munkilib')
else:
    pass

def fail(error):
    """
    ERROR with message from function
    """
    print "ERROR: %s" % error
    sys.exit(1)

def validate_url(name, urlstring):
    if not isinstance(urlstring, basestring):
        fail('%s must be a string' % name)
    try:
        url = urlparse.urlparse(urlstring)
    except:
        fail('%s is not a valid URL' % urlstring)
    if ' ' in urlstring:
        print 'WARNING: %s URL has a space character. Please encode as %%20, else you might have unexpected results' % (urlstring)
    if url.scheme in ['http', 'https', 'file']:
        request = urllib2.Request(urlstring)
        request.get_method = lambda: 'HEAD'
        try:
            response = urllib2.urlopen(request)
        except BaseException as e:
            print 'WARNING: %s URL request failed: %s' % (urlstring, str(e))
    else:
        fail('%s is not a valid URL' % urlstring)


def validate_component(component, workflow):
    """
    Validate components as per the rules of Imagr, for they must be obeyed.
    """
    # Rule 10
    if 'first_boot' in component:
        if str(type(component['first_boot'])) != "<type 'bool'>":
            fail("'first_boot' must be a boolen (<true/> or <false/>). \
                                  Not found in %s" % workflow['name'])
    if 'type' not in component:
        fail("'type' is a required key in a component. Not found in %s" % workflow['name'])

    if component['type'] == 'image':
        # Rule 4
        if 'url' not in component:
            fail("'url' is a required key in an 'image' component. \
                               Not found in %s" % workflow['name'])

        # Rule 5
        if not component['url'].endswith(".dmg") and not \
               component['url'].endswith(".sparseimage"):
            fail("The 'url' in 'image' components must end with '.dmg' or \
                     '.sparseimage'. Not found in %s" % workflow['name'])

        validate_url('Image', component['url'])

    if component['type'] == 'package':
        # Rule 6
        if 'url' not in component:
            fail("'url' is a required key in a 'package' component. \
                               Not found in %s" % workflow['name'])

        # Rule 7
        if not component['url'].endswith(".dmg") and not component['url'].endswith(".pkg"):
            fail("The 'url' in 'package' components must end with '.dmg' or '.pkg'. \
                                               Not found in %s" % workflow['name'])

        validate_url('Package', component['url'])

    if component['type'] == 'script':
        # Rule 8
        if 'content' not in component and 'url' not in component:
            fail("'content' is a required key in a 'script' component. \
                                  Not found in %s" % workflow['name'])
        if 'url' in component:
            validate_url('Script', component['url'])

    if component['type'] == 'partition':
        # Rule 11
        if 'partitions' not in component:
            fail("'partitions' is a required key in a 'partition' component. \
                                        Not found in %s" % workflow['name'])
        if len(component['partitions']) == 0:
            fail("'partitions' must have at least one item in the array. \
                                    Not found in %s" % workflow['name'])
        # Rule 12
        target_found = 0
        size_found = 0
        for partition in component['partitions']:
            if 'target' in partition and partition['target'] is True:
                target_found += 1
            # Rule 13
            if 'size' in partition:
                size_found += 1
        if target_found == 0:
            fail("'partitions' must have at least one 'target'. \
                           Not found in %s" % workflow['name'])
        elif target_found > 1:
            fail("'partitions' must only have one target. \
                Too many found in %s" % workflow['name'])
        if size_found != len(component['partitions']):
            fail("'partitions' must have a size for each partition. \
                        Not enough found in %s" % workflow['name'])

    # Rule 14
    try:
        if (component['type'] == 'partition') and (component['first_boot'] is True):
            fail("'partitions' must not be a first-boot action. \
            'first_boot' = True found in %s" % workflow['name'])
    except:
        pass

    # Rule 15
    try:
        if (component['type'] == 'eraseVolume') and (component['first_boot'] is True):
            fail("'eraseVolume' must not be a first-boot action. \
            'first_boot' = True found in %s" % workflow['name'])
    except:
        pass

    # Rule 19
    try:
        if (component['type'] == 'image') and (type(component['verify']) != bool):
            fail("verify must be a bool, found in %s" % workflow['name'])
    except:
        pass

def main():
    """
    Gimme some main
    """
    temp_plist = None
    parser = argparse.ArgumentParser()
    parser.add_argument('plist', help='Path or URL to your Imagr config plist')
    args = parser.parse_args()

    if 'plist' not in args:
        fail('Path to configuration plist must be specified.')

    plist = args.plist

    # Create a temp file for validation so we can convert to xml freely
    temp_dir = tempfile.mkdtemp()
    temp_plist = os.path.join(temp_dir, 'config.plist')

    plist_url = None
    if plist.startswith('http://') or plist.startswith('https://'):
        plist_url = plist
        temp_dir = tempfile.mkdtemp()
        cmd = ['/usr/bin/curl', '-fsSL', plist, '-o', temp_plist]
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc = task.communicate()[0]

        if task.returncode != 0:
            fail(proc)
        plist = temp_plist

    if not os.path.exists(plist):
        fail("Couldn't find configuration plist at %s" % plist)

    # Lint plist
    cmd = ['/usr/bin/plutil', '-lint', plist]
    task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc = task.communicate()[0]

    if task.returncode != 0:
        fail(proc)

    # Convert to XML so plistlib can read it
    cmd = ['/usr/bin/plutil', '-convert', 'xml1', plist, '-o', temp_plist]
    task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc = task.communicate()[0]

    if task.returncode != 0:
        fail(proc)

    try:
        config = plistlib.readPlist(temp_plist)
    except:
        fail("Couldn't read plist. Make sure it's a valid ")

    if temp_plist:
        shutil.rmtree(temp_dir)

    # Rule 1
    if 'password' in config and len(config['password']) == 0:
        fail('There must be a valid password set.')

    # Rule 2
    if 'workflows' not in config:
        fail('There are no workflows.')

    if len(config['workflows']) == 0:
        fail('There are no workflows.')

    existing_names = []
    for workflow in config['workflows']:
        # Rule 3
        if workflow['name'] in existing_names:
            fail('Workflow names must be unique. %s has already been used.' % workflow['name'])
        else:
            existing_names.append(workflow['name'])

        # Rule 9
        if 'restart_action' in workflow:
            if workflow['restart_action'] != 'none' and workflow['restart_action'] != 'restart' \
                                                  and workflow['restart_action'] != 'shutdown':
                fail("restart_action is not one of 'none', 'shutdown' or 'restart' in workflow %s" \
                                                                              % workflow['name'])

        for component in workflow['components']:
            validate_component(component, workflow)

        # Rule 18
        seen_components = []
        for component in workflow['components']:
            if component.get('type') == 'partition' or component.get('type') == 'image':
                for seen_component in seen_components:
                    if seen_component.get('type') != 'partition' \
                    and seen_component.get('type') != 'image':
                        print 'WARNING: The %s component in workflow %s is a destructive action \
                               that comes after non destructive tasks. This may be intentional, \
                                but the results of the previous actions may be removed from the \
                                      target disk.' % (component.get('type'), workflow['name'])
            seen_components.append(component)

    # Rule 16
    if 'default_workflow' in config and config['default_workflow'] not in existing_names:
        fail('Default workflow must match the name of an existing workflow.')

    # Rule 17
    if 'autorun' in config and config['autorun'] not in existing_names:
        fail('Autorun workflow must match the name of an existing workflow')

    # Rule 20
    if 'background_image' in config:
        validate_url('Background image', config['background_image'])


    # if we get this far, it looks good.
    if plist_url != None:
        plist = plist_url

    print "SUCCESS: %s looks like a valid Imagr configuration plist." % plist

if __name__ == '__main__':
    main()
