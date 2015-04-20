# -*- coding: utf-8 -*-
#
#  MainController.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

import objc
import FoundationPlist
import os
from SystemConfiguration import *
from Foundation import *
from AppKit import *
from Cocoa import *
import subprocess
import sys
import re
import urllib
import re
import macdisk
import urllib2
import Utils
import plistlib
import PyObjCTools

class MainController(NSObject):
    password = objc.IBOutlet()
    passwordLabel = objc.IBOutlet()
    loginLabel = objc.IBOutlet()
    loginButton = objc.IBOutlet()
    errorField = objc.IBOutlet()
    mainWindow = objc.IBOutlet()

    mainView = objc.IBOutlet()
    loginView = objc.IBOutlet()

    progressPanel = objc.IBOutlet()
    progressIndicator = objc.IBOutlet()
    progressText = objc.IBOutlet()

    startUpDiskPanel = objc.IBOutlet()
    startUpDiskText = objc.IBOutlet()
    startupDiskCancelButton = objc.IBOutlet()
    startupDiskDropdown = objc.IBOutlet()
    startupDiskRestartButton = objc.IBOutlet()

    chooseTargetPanel = objc.IBOutlet()
    chooseTargetDropDown = objc.IBOutlet()
    chooseTargetCancelButton = objc.IBOutlet()
    chooseTargetPanelSelectTarget = objc.IBOutlet()

    cancelAndRestartButton = objc.IBOutlet()
    chooseWorkflowDropDown = objc.IBOutlet()
    chooseWorkflowLabel = objc.IBOutlet()

    runWorkflowButton = objc.IBOutlet()
    workflowDescriptionView = objc.IBOutlet()
    workflowDescription = objc.IBOutlet()

    imagingProgress = objc.IBOutlet()
    imagingLabel = objc.IBOutlet()
    imagingProgressPanel = objc.IBOutlet()

    # former globals, now instance variables
    volumes = None
    passwordHash = None
    workflows = None
    targetVolume = None
    workVolume = None
    selectedWorkflow = None
    packages_to_install = None

    def awakeFromNib(self):
        self.loginView.setHidden_(self)
        self.progressPanel.center()
        self.password.becomeFirstResponder()
        # Run app startup - get the images, password, volumes - anything that takes a while

        self.progressText.setStringValue_("Application Starting...")
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel,
                                                                self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
                                                            self.loadData, self, None)

    def loadData(self):

        pool = NSAutoreleasePool.alloc().init()
        self.volumes = macdisk.MountedVolumes()

        theURL = Utils.getServerURL()
        if theURL:
            plistData = Utils.downloadFile(theURL)
            converted_plist = FoundationPlist.readPlistFromString(plistData)
            self.passwordHash = converted_plist['password']
            self.workflows = converted_plist['workflows']
            #NSLog(str(workflows))
        else:
            self.passwordHash = False

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
                                                                   self.loadDataComplete, None, YES)
        del pool

    def loadDataComplete(self):
        #global passwordHash
        # end modal sheet and close the panel
        NSApp.endSheet_(self.progressPanel)
        if not self.passwordHash:
            self.password.setEnabled_(False)
            self.loginButton.setEnabled_(False)
            self.disableAllButtons(self)
            self.startUpDiskText.setStringValue_("No Server URL has been set. Please contact your administrator.")
            self.setStartupDisk_(self)
        self.progressPanel.orderOut_(self)
        self.loginView.setHidden_(False)
        self.mainView.setHidden_(self)
        return

    @objc.IBAction
    def login_(self, sender):
        #global volumes
        #global passwordHash

        password_value = self.password.stringValue()
        if Utils.getPasswordHash(password_value) != self.passwordHash and password_value != "":
            self.errorField.setEnabled_(sender)
            self.errorField.setStringValue_("Incorrect password")
        else:
            self.loginView.setHidden_(sender)
            self.mainView.setHidden_(False)
            self.chooseImagingTarget_(sender)
            self.enableAllButtons_(self)

    @objc.IBAction
    def setStartupDisk_(self, sender):
        #global volumes
        # This stops the console being spammed with: unlockFocus called too many times. Called on <NSButton
        NSGraphicsContext.saveGraphicsState()
        self.disableAllButtons(sender)
        # clear out the default junk in the dropdown
        self.startupDiskDropdown.removeAllItems()
        list = []
        for volume in self.volumes:
            list.append(volume.mountpoint)

        # Let's add the items to the popup
        self.startupDiskDropdown.addItemsWithTitles_(list)
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.startUpDiskPanel, self.mainWindow, self, None, None)
        NSGraphicsContext.restoreGraphicsState()

    @objc.IBAction
    def closeStartUpDisk_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.startUpDiskPanel)
        self.startUpDiskPanel.orderOut_(self)

    @objc.IBAction
    def openProgress_(self, sender):
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel, self.mainWindow, self, None, None)

    @objc.IBAction
    def chooseImagingTarget_(self, sender):
        self.disableAllButtons(sender)
        NSGraphicsContext.saveGraphicsState()
        #global volumes
        #global targetVolume
        #global workVolume
        self.chooseTargetDropDown.removeAllItems()
        list = []
        for volume in self.volumes:
            if volume.mountpoint != '/':
                if volume.mountpoint.startswith("/Volumes"):
                    if volume.mountpoint != '/Volumes':
                        if volume.writable:
                            list.append(volume.mountpoint)
         # No writable volumes, this is bad.
        if len(list) == 0:
           alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(                                                                                                        NSLocalizedString(u"No writable volumes found", None),                                                                                                                      NSLocalizedString(u"Restart", None),                                                                                                                      NSLocalizedString(u"Open Disk Utility", None),                                                                                                                      objc.nil,                                                                                                                    NSLocalizedString(u"No writable volumes were found on this Mac.", None))

           alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(self.mainWindow, self, self.noVolAlertDidEnd_returnCode_contextInfo_, objc.nil)
        # If there's only one volume, we're going to use that and move on to selecting the workflow
        self.enableAllButtons_(self)
        if len(list) == 1:
            self.targetVolume = list[0]
            self.selectWorkflow_(sender)
            for volume in self.volumes:
                if str(volume.mountpoint) == str(self.targetVolume):
                    imaging_target = volume
                    self.workVolume = volume
                    break
            # We'll move on to the select workflow bit when it exists
        else:
            self.chooseTargetDropDown.addItemsWithTitles_(list)
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.chooseTargetPanel, self.mainWindow, self, None, None)
        NSGraphicsContext.restoreGraphicsState()

    @PyObjCTools.AppHelper.endSheetMethod
    def noVolAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        if returncode == NSAlertDefaultReturn:
            self.setStartupDisk_(sender)
        else:
            cmd = ['/Applications/Utilities/Disk Utility.app/Contents/MacOS/Disk Utility']
            proc = subprocess.call(cmd)
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(                                                                                                        NSLocalizedString(u"Rescan for volumes", None),                                                                                                                      NSLocalizedString(u"Rescan", None),                                                                                                                      objc.nil,                                                                                                                      objc.nil,                                                                                                                    NSLocalizedString(u"Rescan for volumes.", None))

            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(self.mainWindow, self, self.rescanAlertDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def rescanAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        self.progressText.setStringValue_("Reloading Volumes...")
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel,
                                                                self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
                                                            self.loadData, self, None)
    @objc.IBAction
    def selectImagingTarget_(self, sender):
        #global targetVolume
        #global workVolume
        self.targetVolume = self.chooseTargetDropDown.titleOfSelectedItem()
        for volume in self.volumes:
            if str(volume.mountpoint) == str(self.targetVolume):
                self.workVolume = volume
                break
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.chooseTargetPanel)
        self.chooseTargetPanel.orderOut_(self)
        self.selectWorkflow_(self)


    @objc.IBAction
    def closeImagingTarget_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.chooseTargetPanel)
        self.chooseTargetPanel.orderOut_(self)
        self.setStartupDisk_(sender)

    @objc.IBAction
    def selectWorkflow_(self, sender):
        #global targetVolume
        #global workflows
        self.chooseWorkflowDropDown.removeAllItems()
        list = []
        for workflow in self.workflows:
            list.append(workflow['name'])

        self.chooseWorkflowDropDown.addItemsWithTitles_(list)
        self.chooseWorkflowLabel.setHidden_(False)
        self.chooseWorkflowDropDown.setHidden_(False)
        self.workflowDescriptionView.setHidden_(False)
        self.runWorkflowButton.setHidden_(False)
        self.chooseWorkflowDropDownDidChange_(sender)

    @objc.IBAction
    def chooseWorkflowDropDownDidChange_(self, sender):
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                try:
                    self.workflowDescription.setString_(workflow['description'])
                except:
                    self.workflowDescription.setString_("")
                break

    @objc.IBAction
    def runWorkflow_(self, sender):
        self.imagingProgress.setHidden_(False)
        self.imagingLabel.setHidden_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.chooseWorkflowLabel.setEnabled_(True)
        self.chooseWorkflowDropDown.setEnabled_(False)
        #self.workflowDescriptionView.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.imagingLabel.setStringValue_("Preparing to run workflow...")
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.imagingProgressPanel,
                                                                self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
                                                            self.imageOnThread, self, None)

    def Clone(self, source, target, erase=True, verify=True, show_activity=True):
        """A wrapper around 'asr' to clone one disk object onto another.

        We run with --puppetstrings so that we get non-buffered output that we can
        actually read when show_activity=True.

        Args:
            source: A Disk or Image object.
            target: A Disk object (including a Disk from a mounted Image)
            erase:  Whether to erase the target. Defaults to True.
            verify: Whether to verify the clone operation. Defaults to True.
            show_activity: whether to print the progress to the screen.
        Returns:
            boolean: whether the operation succeeded.
        Raises:
            MacDiskError: source is not a Disk or Image object
            MacDiskError: target is not a Disk object
        """

        #global volumes
        #global workVolume
        # if isinstance(source, macdisk.Image):
        #     # even attached dmgs can be a restore source as path to the dmg
        #     source_ref = source.imagepath
        # elif isinstance(source, macdisk.Disk):
        #     source_ref = "/dev/%s" % source.deviceidentifier
        # else:
        #     raise macdisk.MacDiskError("source is not a Disk or Image object")

        for volume in self.volumes:
            if str(volume.mountpoint) == str(target):
                imaging_target = volume
                self.workVolume = volume
                break

        if isinstance(imaging_target, macdisk.Disk):
            target_ref = "/dev/%s" % imaging_target.deviceidentifier
        else:
            raise macdisk.MacDiskError("target is not a Disk object")



        command = ["/usr/sbin/asr", "restore", "--source", str(source), "--target",
                             target_ref, "--noprompt", "--puppetstrings"]

        if erase:
            # check we can unmount the target... may as well fail here than later.
            if imaging_target.Mounted():
                imaging_target.Unmount()
            command.append("--erase")

        if not verify:
            command.append("--noverify")

        self.imagingProgress.setMinValue_(0.0)
        self.imagingProgress.setMaxValue_(100.0)
        self.imagingProgress.setIndeterminate_(True)
        self.imagingProgress.setUsesThreadedAnimation_(True)
        self.imagingProgress.startAnimation_(True)
        self.imagingProgress.setDoubleValue_(float(0.001))
        NSLog(str(command))
        task = subprocess.Popen(command, stdout=subprocess.PIPE,
                                                        stderr=subprocess.PIPE)

        message = " "
        while task.poll() is None:
            output = task.stdout.readline().strip()
            try:
                percent = int(output.split("\t")[1])
            except:
                percent = 0.001
            if len(output.split("\t")) == 4:
                if output.split("\t")[3] == "restore":
                    message = "Restoring: "+ str(percent) + "%"

                elif output.split("\t")[3] == "verify":
                    message = "Verifying: "+ str(percent) + "%"
                else:
                    message = " "
            else:
                message = " "
            if percent == 0:
                percent = 0.001
            self.imagingProgress.setIndeterminate_(False)
            self.imagingProgress.setDoubleValue_(float(percent))
            self.imagingProgress.setNeedsDisplay_(True)
            self.imagingLabel.setStringValue_(str(message))
            self.imagingLabel.setNeedsDisplay_(True)

        (unused_stdout, stderr) = task.communicate()

        if task.returncode:
            raise macdisk.MacDiskError("Cloning Error: %s" % stderr)
        if task.poll() == 0:
            return True

    def imageOnThread(self, sender):
        #global targetVolume
        #global volumes
        #global selectedWorkflow
        pool = NSAutoreleasePool.alloc().init()
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        # let's get the workflow
        dmg = None
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                self.selectedWorkflow = workflow
                for item in workflow['components']:
                    if item['type'] == 'image':
                        dmg = item['url']
                        break
        if dmg:
            self.Clone(dmg, self.targetVolume)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
                                                                   self.imageOnThreadComplete, None, YES)
        del pool

    def imageOnThreadComplete(self, sender):
        #global selectedWorkflow
        #global packages_to_install
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)
        self.packages_to_install = False
        pre_first_boot = False
        for item in self.selectedWorkflow['components']:
            if item['type'] == 'package':
                if 'pre_first_boot' in item:
                    pre_first_boot = True
                self.packages_to_install = True
                break

        if pre_first_boot:
            # have packages to install
            self.downloadAndInstallPackages_(sender)
        elif self.packages_to_install:
            # got packages to install at first boot, let's process those
            self.downloadAndCopyPackages_(sender)
        else:
            # We're done!
            self.restartToImagedVolume_(sender)

    def downloadAndInstallPackages_(self, sender):
        #global packages_to_install
        #global workVolume
        #global selectedWorkflow
        self.progressText.setStringValue_("Installing Packages...")
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel,
                                                                self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.downloadAndInstallPackagesOnThread_(sender),
                                                                self, None)

    def downloadAndInstallPackagesOnThread_(self, sender):
        pool = NSAutoreleasePool.alloc().init()

        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and item.get('pre_first_boot')]
        package_count = len(pkgs_to_install)
        counter = 0
        for item in pkgs_to_install:
            counter = counter + 1
            Utils.downloadAndInstallPackage(
                item['url'], self.workVolume.mountpoint, counter, package_count)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
                                                                   self.downloadAndInstallComplete_(sender), None, YES)
        del pool

    def downloadAndInstallComplete_(self, sender):
        # are there more pkgs to install at first boot?
        first_boot_pkgs_to_install = [item for item in self.selectedWorkflow['components']
                                      if item.get('type') == 'package'
                                      and not item.get('pre_first_boot')]
        if first_boot_pkgs_to_install:
            self.downloadAndCopyPackages_(sender)
        else:
            self.restartToImagedVolume_(sender)

    def downloadAndCopyPackages_(self, sender):

        #global workVolume
        #global selectedWorkflow
        self.progressText.setStringValue_("Copying packages for install on first boot...")
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(self.progressPanel,
                                                                self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
                                                            self.downloadAndCopyPackagesOnThread_, self, None)


    def downloadAndCopyPackagesOnThread_(self, sender):
        pool = NSAutoreleasePool.alloc().init()
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        packages_dir = os.path.join(self.workVolume.mountpoint, 'usr/local/first-boot/')
        if not os.path.exists(packages_dir):
            os.makedirs(packages_dir)
        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and not item.get('pre_first_boot')]
        package_count = len(pkgs_to_install)
        counter = 0
        # download packages to /usr/local/first-boot - append number
        for item in pkgs_to_install:
            counter = counter + 1
            Utils.downloadPackage(item['url'], self.workVolume.mountpoint, counter, package_count)
        # copy bits for first boot script
        Utils.copyFirstBoot(self.workVolume.mountpoint)
        # restart
        del pool
        self.restartToImagedVolume_(sender)

    def restartToImagedVolume_(self, sender):
        # set the startup disk to the restored volume

        self.workVolume.SetStartupDisk()

        cmd = ['/sbin/reboot']
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
        task.communicate()
    def enableAllButtons_(self, sender):
        self.cancelAndRestartButton.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(True)

    def disableAllButtons(self, sender):
        self.cancelAndRestartButton.setEnabled_(False)
        self.runWorkflowButton.setEnabled_(False)
