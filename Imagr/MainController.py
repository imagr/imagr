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
import macdisk
import urllib2
import Utils
import PyObjCTools

class MainController(NSObject):

    mainWindow = objc.IBOutlet()

    theTabView = objc.IBOutlet()
    introTab = objc.IBOutlet()
    loginTab = objc.IBOutlet()
    mainTab = objc.IBOutlet()
    errorTab = objc.IBOutlet()

    password = objc.IBOutlet()
    passwordLabel = objc.IBOutlet()
    loginLabel = objc.IBOutlet()
    loginButton = objc.IBOutlet()
    errorField = objc.IBOutlet()

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
    imagingProgressDetail = objc.IBOutlet()

    # former globals, now instance variables
    volumes = None
    passwordHash = None
    workflows = None
    targetVolume = None
    workVolume = None
    selectedWorkflow = None
    packages_to_install = None
    restartAction = None
    blessTarget = None
    errorMessage = None
    alert = None

    def errorPanel(self, error):
        errorText = str(error)
        self.alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(errorText, None),
            NSLocalizedString(u"Okay", None),
            objc.nil,
            objc.nil,
            NSLocalizedString(u"", None))

        self.alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, self.setStartupDisk_, objc.nil)

    def runStartupTasks(self):
        self.mainWindow.center()
        # Run app startup - get the images, password, volumes - anything that takes a while

        self.progressText.setStringValue_("Application Starting...")
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    def loadData(self):

        pool = NSAutoreleasePool.alloc().init()
        self.volumes = macdisk.MountedVolumes()

        theURL = Utils.getServerURL()
        if theURL:
            plistData = Utils.downloadFile(theURL)
            if plistData:
                try:
                    converted_plist = FoundationPlist.readPlistFromString(plistData)
                except:
                    self.errorMessage = "Configuration plist couldn't be read."
                try:
                    self.passwordHash = converted_plist['password']
                except:
                    self.errorMessage = "Password wasn't set."

                try:
                    self.workflows = converted_plist['workflows']
                except:
                    self.errorMessage = "No workflows found in the configuration plist."
            else:
                self.errorMessage = "Couldn't get configuration plist from server."
        else:
            self.errorMessage = "Configuration URL wasn't set."

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.loadDataComplete, None, YES)
        del pool

    def loadDataComplete(self):
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel(self.errorMessage)
        else:
            self.theTabView.selectTabViewItem_(self.loginTab)
            self.mainWindow.makeFirstResponder_(self.password)

    @objc.IBAction
    def login_(self, sender):
        if self.passwordHash:
            password_value = self.password.stringValue()
            if Utils.getPasswordHash(password_value) != self.passwordHash or password_value == "":
                self.errorField.setEnabled_(sender)
                self.errorField.setStringValue_("Incorrect password")
            else:
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(sender)
                self.enableAllButtons_(self)

    @objc.IBAction
    def setStartupDisk_(self, sender):
        if self.alert:
            self.alert.window().orderOut_(self)
            self.alert = None

        self.restartAction = 'restart'
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
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.startUpDiskPanel, self.mainWindow, self, None, None)
        NSGraphicsContext.restoreGraphicsState()

    @objc.IBAction
    def closeStartUpDisk_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.startUpDiskPanel)
        self.startUpDiskPanel.orderOut_(self)

    @objc.IBAction
    def openProgress_(self, sender):
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.progressPanel, self.mainWindow, self, None, None)

    @objc.IBAction
    def chooseImagingTarget_(self, sender):
        self.disableAllButtons(sender)
        NSGraphicsContext.saveGraphicsState()
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
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                NSLocalizedString(u"No writable volumes found", None),
                NSLocalizedString(u"Restart", None),
                NSLocalizedString(u"Open Disk Utility", None),
                objc.nil,
                NSLocalizedString(u"No writable volumes were found on this Mac.", None))

            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.mainWindow, self, self.noVolAlertDidEnd_returnCode_contextInfo_, objc.nil)
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
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.chooseTargetPanel, self.mainWindow, self, None, None)
        NSGraphicsContext.restoreGraphicsState()

    @PyObjCTools.AppHelper.endSheetMethod
    def noVolAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        if returncode == NSAlertDefaultReturn:
            self.setStartupDisk_(None)
        else:
            cmd = ['/Applications/Utilities/Disk Utility.app/Contents/MacOS/Disk Utility']
            proc = subprocess.call(cmd)
            #NSWorkspace.sharedWorkspace().launchApplication_("/Applications/Utilities/Disk Utility.app")
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                NSLocalizedString(u"Rescan for volumes", None),
                NSLocalizedString(u"Rescan", None),
                objc.nil,
                objc.nil,
                NSLocalizedString(u"Rescan for volumes.", None))

            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.mainWindow, self, self.rescanAlertDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def rescanAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        self.progressText.setStringValue_("Reloading Volumes...")
        self.theTabView.selectTabViewItem_(self.introTab)
        # NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
        #     self.progressPanel, self.mainWindow, self, None, None)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)


    @objc.IBAction
    def selectImagingTarget_(self, sender):
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
        '''Set up the selected workflow to run on secondary thread'''
        self.imagingProgress.setHidden_(False)
        self.imagingLabel.setHidden_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.chooseWorkflowLabel.setEnabled_(True)
        self.chooseWorkflowDropDown.setEnabled_(False)
        # self.workflowDescriptionView.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.imagingLabel.setStringValue_("Preparing to run workflow...")
        self.imagingProgressDetail.setStringValue_('')
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.imagingProgressPanel, self.mainWindow, self, None, None)
        # initialize the progress bar
        self.imagingProgress.setMinValue_(0.0)
        self.imagingProgress.setMaxValue_(100.0)
        self.imagingProgress.setIndeterminate_(True)
        self.imagingProgress.setUsesThreadedAnimation_(True)
        self.imagingProgress.startAnimation_(self)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
            self.processWorkflowOnThread, self, None)

    def updateProgressWithInfo_(self, info):
        '''UI stuff should be done on the main thread. Yet we do all our interesting work
        on a secondary thread. So to update the UI, the secondary thread should call this
        method using performSelectorOnMainThread_withObject_waitUntilDone_'''
        if 'title' in info.keys():
            self.imagingLabel.setStringValue_(info['title'])
        if 'percent' in info.keys():
            if float(info['percent']) < 0:
                if not self.imagingProgress.isIndeterminate():
                    self.imagingProgress.setIndeterminate_(True)
                    self.imagingProgress.startAnimation_(self)
            else:
                if self.imagingProgress.isIndeterminate():
                    self.imagingProgress.stopAnimation_(self)
                    self.imagingProgress.setIndeterminate_(False)
                self.imagingProgress.setDoubleValue_(float(info['percent']))
        if 'detail' in info.keys():
            self.imagingProgressDetail.setStringValue_(info['detail'])

    def updateProgressTitle_Percent_Detail_(self, title, percent, detail):
        '''Wrapper method that calls the UI update method on the main thread'''
        info = {}
        if title is not None:
            info['title'] = title
        if percent is not None:
            info['percent'] = percent
        if detail is not None:
            info['detail'] = detail
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.updateProgressWithInfo_, info, objc.NO)

    def processWorkflowOnThread(self, sender):
        '''Process the selected workflow'''
        pool = NSAutoreleasePool.alloc().init()
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        # let's get the workflow
        self.selectedWorkflow = None
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                self.selectedWorkflow = workflow
                break
        if self.selectedWorkflow:
            if 'restart_action' in self.selectedWorkflow:
                self.restartAction = self.selectedWorkflow['restart_action']
            if 'bless_target' in self.selectedWorkflow:
                self.blessTarget = self.selectedWorkflow['bless_target']
            else:
                self.blessTarget = True

            self.restoreImage()
            self.downloadAndInstallPackages()
            self.downloadAndCopyPackages()
            self.copyFirstBootScripts()
            self.runPreFirstBootScript()

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.processWorkflowOnThreadComplete, None, YES)
        del pool

    def processWorkflowOnThreadComplete(self):
        '''Done running workflow, restart to imaged volume'''
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)
        if self.restartAction == 'restart' or self.restartAction == 'shutdown':
            self.restartToImagedVolume()
        else:
            self.openEndWorkflowPanel()

    def restoreImage(self):
        dmgs_to_restore = [item.get('url') for item in self.selectedWorkflow['components']
                           if item.get('type') == 'image' and item.get('url')]
        if dmgs_to_restore:
            self.Clone(dmgs_to_restore[0], self.targetVolume)

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

        for volume in self.volumes:
            if str(volume.mountpoint) == str(target):
                imaging_target = volume
                self.workVolume = volume
                break

        if isinstance(imaging_target, macdisk.Disk):
            target_ref = "/dev/%s" % imaging_target.deviceidentifier
        else:
            raise macdisk.MacDiskError("target is not a Disk object")

        command = ["/usr/sbin/asr", "restore", "--source", str(source),
                   "--target", target_ref, "--noprompt", "--puppetstrings"]

        if erase:
            # check we can unmount the target... may as well fail here than later.
            if imaging_target.Mounted():
                imaging_target.Unmount()
            command.append("--erase")

        if not verify:
            command.append("--noverify")

        self.updateProgressTitle_Percent_Detail_('Restoring %s' % source, -1, '')

        NSLog(str(command))
        task = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        message = ""
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
                    message = ""
            else:
                message = ""
            if percent == 0:
                percent = 0.001
            self.updateProgressTitle_Percent_Detail_(None, percent, message)

        (unused_stdout, stderr) = task.communicate()

        if task.returncode:
            raise macdisk.MacDiskError("Cloning Error: %s" % stderr)
        if task.poll() == 0:
            return True

    def downloadAndInstallPackages(self):
        self.updateProgressTitle_Percent_Detail_('Installing packages...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and item.get('pre_first_boot')]
        for item in pkgs_to_install:
            package_name = os.path.basename(item['url'])
            Utils.downloadAndInstallPackage(
                item['url'], self.workVolume.mountpoint,
                progress_method=self.updateProgressTitle_Percent_Detail_)

    def downloadAndCopyPackages(self):
        self.updateProgressTitle_Percent_Detail_(
            'Copying packages for install on first boot...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        pkgs_to_install = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'package' and not item.get('pre_first_boot')]
        package_count = len(pkgs_to_install)
        counter = 0.0
        # download packages to /usr/local/first-boot - prepend number
        for item in pkgs_to_install:
            counter = counter + 1.0
            package_name = os.path.basename(item['url'])
            Utils.downloadPackage(item['url'], self.workVolume.mountpoint, counter,
                                  progress_method=self.updateProgressTitle_Percent_Detail_)
        if package_count:
            # copy bits for first boot script
            packages_dir = os.path.join(self.workVolume.mountpoint, 'usr/local/first-boot/')
            if not os.path.exists(packages_dir):
                os.makedirs(packages_dir)
            Utils.copyFirstBoot(self.workVolume.mountpoint)

    def copyFirstBootScripts(self):
        if not self.workVolume.Mounted():
            self.workVolume.Mount()

        scripts_to_run = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'script' and not item.get('pre_first_boot')]
        script_count = len(scripts_to_run)
        counter = 0.0
        NSLog(str(scripts_to_run))
        for item in scripts_to_run:
            counter = counter + 1.0
            script = item['content']
            Utils.copyScript(
                script, self.workVolume.mountpoint, counter,
                progress_method=self.updateProgressTitle_Percent_Detail_)
        if scripts_to_run:
            Utils.copyFirstBoot(self.workVolume.mountpoint)

    def runPreFirstBootScript(self):
        self.updateProgressTitle_Percent_Detail_(
            'Preparing to run scripts...', -1, '')
        # mount the target
        if not self.workVolume.Mounted():
            self.workVolume.Mount()
        scripts_to_run = [item for item in self.selectedWorkflow['components']
                           if item.get('type') == 'script' and item.get('pre_first_boot')]
        script_count = len(scripts_to_run)
        counter = 0.0
        NSLog(str(scripts_to_run))
        for item in scripts_to_run:
            script = item['content']
            Utils.runScript(
                script, self.workVolume.mountpoint,
                progress_method=self.updateProgressTitle_Percent_Detail_)


    @objc.IBAction
    def restartButtonClicked_(self, sender):
        NSLog("Restart Button Clicked")
        self.restartToImagedVolume()

    def restartToImagedVolume(self):
        # set the startup disk to the restored volume
        if self.blessTarget == True:
            self.workVolume.SetStartupDisk()
        if self.restartAction == 'restart':
            cmd = ['/sbin/reboot']
        elif self.restartAction == 'shutdown':
            cmd = ['/sbin/shutdown', '-h', 'now']
        task = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        task.communicate()

    def openEndWorkflowPanel(self):
        label_string = "%s completed." % self.selectedWorkflow['name']
        alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(label_string, None),
            NSLocalizedString(u"Restart", None),
            NSLocalizedString(u"Run another workflow", None),
            NSLocalizedString(u"Shutdown", None),
            NSLocalizedString(u"", None),)

        alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, self.endWorkflowAlertDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def endWorkflowAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        # -1 = Shutdown
        # 0 = another workflow
        # 1 = Restart
        if returncode == -1:
            self.restartAction = 'shutdown'
            self.restartToImagedVolume()
        elif returncode == 1:
            self.restartAction = 'restart'
            self.restartToImagedVolume()
        elif returncode == 0:
            self.chooseWorkflowDropDown.setEnabled_(True)
            self.chooseImagingTarget_(contextinfo)

    def enableAllButtons_(self, sender):
        self.cancelAndRestartButton.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(True)

    def disableAllButtons(self, sender):
        self.cancelAndRestartButton.setEnabled_(False)
        self.runWorkflowButton.setEnabled_(False)

    @objc.IBAction
    def runDiskUtility_(self, sender):
        NSWorkspace.sharedWorkspace().launchApplication_("/Applications/Utilities/Disk Utility.app")

    @objc.IBAction
    def runTerminal_(self, sender):
        NSWorkspace.sharedWorkspace().launchApplication_("/Applications/Utilities/Terminal.app")
