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
import tempfile
import shutil
import Quartz

class MainController(NSObject):

    mainWindow = objc.IBOutlet()

    utilities_menu = objc.IBOutlet()
    help_menu = objc.IBOutlet()

    theTabView = objc.IBOutlet()
    introTab = objc.IBOutlet()
    loginTab = objc.IBOutlet()
    mainTab = objc.IBOutlet()
    errorTab = objc.IBOutlet()
    computerNameTab = objc.IBOutlet()

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
    reloadWorkflowsButton = objc.IBOutlet()
    reloadWorkflowsMenuItem = objc.IBOutlet()
    chooseWorkflowDropDown = objc.IBOutlet()
    chooseWorkflowLabel = objc.IBOutlet()

    runWorkflowButton = objc.IBOutlet()
    workflowDescriptionView = objc.IBOutlet()
    workflowDescription = objc.IBOutlet()

    imagingProgress = objc.IBOutlet()
    imagingLabel = objc.IBOutlet()
    imagingProgressPanel = objc.IBOutlet()
    imagingProgressDetail = objc.IBOutlet()

    computerNameInput = objc.IBOutlet()
    computerNameButton = objc.IBOutlet()

    # former globals, now instance variables
    hasLoggedIn = None
    volumes = None
    passwordHash = None
    workflows = None
    targetVolume = None
    #workVolume = None
    selectedWorkflow = None
    defaultWorkflow = None
    parentWorkflow = None
    packages_to_install = None
    restartAction = None
    blessTarget = None
    errorMessage = None
    alert = None
    workflow_is_running = False
    computerName = None
    counter = 0.0
    first_boot_items = None

    def errorPanel(self, error):
        if error:
            errorText = str(error)
        else:
            errorText = "Unknown error"

        # Send a report to the URL if it's configured
        Utils.sendReport('error', errorText)

        self.alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(errorText, None),
            NSLocalizedString(u"Choose Startup Disk", None),
            NSLocalizedString(u"Reload Workflows", None),
            objc.nil,
            NSLocalizedString(u"", None))

        self.errorMessage = None
        self.alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, self.errorPanelDidEnd_returnCode_contextInfo_, objc.nil)

    @PyObjCTools.AppHelper.endSheetMethod
    def errorPanelDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        # 0 = reload workflows
        # 1 = Restart
        if returncode == 0:
            self.errorMessage = None
            self.reloadWorkflows_(self)
        else:
            self.setStartupDisk_(self)

    def runStartupTasks(self):
        self.mainWindow.center()
        # Run app startup - get the images, password, volumes - anything that takes a while

        self.progressText.setStringValue_("Application Starting...")
        self.chooseWorkflowDropDown.removeAllItems()
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        self.registerForWorkspaceNotifications()
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    def registerForWorkspaceNotifications(self):
        nc = NSWorkspace.sharedWorkspace().notificationCenter()
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived, NSWorkspaceDidMountNotification, None)
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived, NSWorkspaceDidUnmountNotification, None)
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived, NSWorkspaceDidRenameVolumeNotification, None)

    def wsNotificationReceived(self, notification):
        if self.workflow_is_running:
            self.should_update_volume_list = True
            return
        notification_name = notification.name()
        user_info = notification.userInfo()
        NSLog("NSWorkspace notification was: %@", notification_name)
        if notification_name == NSWorkspaceDidMountNotification:
            new_volume = user_info['NSDevicePath']
            NSLog("%@ was mounted", new_volume)
        elif notification_name == NSWorkspaceDidUnmountNotification:
            removed_volume = user_info['NSDevicePath']
            NSLog("%@ was unmounted", removed_volume)
        elif notification_name == NSWorkspaceDidRenameVolumeNotification:
            pass
        # this repeats code elsewhere; this should really be factored out
        # this next bit can take a bit and cause rainbow wheels; we should also
        # do this differently.
        self.volumes = macdisk.MountedVolumes()
        self.chooseTargetDropDown.removeAllItems()
        list = []
        for volume in self.volumes:
            if volume.mountpoint != '/':
                if volume.mountpoint.startswith("/Volumes"):
                    if volume.mountpoint != '/Volumes':
                        if volume.writable:
                            list.append(volume.mountpoint)
        self.chooseTargetDropDown.addItemsWithTitles_(list)
        # reselect previously selected target if possible
        if self.targetVolume:
            self.chooseTargetDropDown.selectItemWithTitle_(self.targetVolume)
            selected_volume = self.chooseTargetDropDown.titleOfSelectedItem()
        else:
            selected_volume = list[0]
            self.chooseTargetDropDown.selectItemWithTitle_(selected_volume)
        for volume in self.volumes:
            if str(volume.mountpoint) == str(selected_volume):
                self.targetVolume = volume

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
                    # Bypass the login form if no password is given.
                    self.hasLoggedIn = True

                try:
                    self.workflows = converted_plist['workflows']
                except:
                    self.errorMessage = "No workflows found in the configuration plist."
                try:
                    self.defaultWorkflow = converted_plist['default_workflow']
                except:
                    pass
            else:
                self.errorMessage = "Couldn't get configuration plist from server."
        else:
            self.errorMessage = "Configuration URL wasn't set."
        Utils.setup_logging()
        Utils.sendReport('in_progress', 'Imagr is starting up...')
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.loadDataComplete, None, YES)
        del pool

    def loadDataComplete(self):
        #self.reloadWorkflowsMenuItem.setEnabled_(True)
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel(self.errorMessage)
        else:
            self.buildUtilitiesMenu()
            if self.hasLoggedIn:
                self.enableWorkflowViewControls()
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(None)
                #self.enableAllButtons_(self)
            else:
                self.theTabView.selectTabViewItem_(self.loginTab)
                self.mainWindow.makeFirstResponder_(self.password)

    @objc.IBAction
    def reloadWorkflows_(self, sender):
        self.reloadWorkflowsMenuItem.setEnabled_(False)
        self.progressText.setStringValue_("Reloading workflows...")
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        self.theTabView.selectTabViewItem_(self.introTab)
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    @objc.IBAction
    def login_(self, sender):
        if self.passwordHash:
            password_value = self.password.stringValue()
            if Utils.getPasswordHash(password_value) != self.passwordHash or password_value == "":
                self.errorField.setEnabled_(sender)
                self.errorField.setStringValue_("Incorrect password")
                self.shakeWindow()

            else:
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(None)
                self.enableAllButtons_(self)
                self.hasLoggedIn = True

    @objc.IBAction
    def setStartupDisk_(self, sender):
        if self.alert:
            self.alert.window().orderOut_(self)
            self.alert = None

        # Prefer to use the built in Startup disk pane
        if os.path.exists("/Applications/Utilities/Startup Disk.app"):
            Utils.launchApp("/Applications/Utilities/Startup Disk.app")
        else:
            self.restartAction = 'restart'
            # This stops the console being spammed with: unlockFocus called too many times. Called on <NSButton
            NSGraphicsContext.saveGraphicsState()
            self.disableAllButtons_(sender)
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
        else:
            self.chooseTargetDropDown.addItemsWithTitles_(list)
            if self.targetVolume:
                self.chooseTargetDropDown.selectItemWithTitle_(self.targetVolume.mountpoint)

            selected_volume = self.chooseTargetDropDown.titleOfSelectedItem()
            for volume in self.volumes:
                if str(volume.mountpoint) == str(selected_volume):
                    #imaging_target = volume
                    self.targetVolume = volume
                    break
            self.selectWorkflow_(sender)

    @PyObjCTools.AppHelper.endSheetMethod
    def noVolAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):
        if returncode == NSAlertDefaultReturn:
            self.setStartupDisk_(None)
        else:
            Utils.launchApp('/Applications/Utilities/Disk Utility.app')
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
        # NSWorkspaceNotifications should take care of updating our list of available volumes
        # Need to reload workflows
        self.reloadWorkflows_(self)

    @objc.IBAction
    def selectImagingTarget_(self, sender):
        volume_name = self.chooseTargetDropDown.titleOfSelectedItem()
        for volume in self.volumes:
            if str(volume.mountpoint) == str(volume_name):
                self.targetVolume = volume
                break
        NSLog("Imaging target is %@", self.targetVolume)


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
            if 'hidden' in workflow:
                # Don't add 'hidden' workflows to the list
                if workflow['hidden'] == False:
                    list.append(workflow['name'])
            else:
                # If not specified, assume visible
                list.append(workflow['name'])

        self.chooseWorkflowDropDown.addItemsWithTitles_(list)

        # The current selection is deselected if a nil or non-existent title is given
        if self.defaultWorkflow:
            self.chooseWorkflowDropDown.selectItemWithTitle_(self.defaultWorkflow)

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

    def enableWorkflowDescriptionView_(self, enabled):
        # See https://developer.apple.com/library/mac/qa/qa1461/_index.html
        self.workflowDescription.setSelectable_(enabled)
        if enabled:
            self.workflowDescription.setTextColor_(NSColor.controlTextColor())
        else:
            self.workflowDescription.setTextColor_(NSColor.disabledTextColor())

    def disableWorkflowViewControls(self):
        self.reloadWorkflowsButton.setEnabled_(False)
        self.reloadWorkflowsMenuItem.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)
        self.chooseWorkflowLabel.setEnabled_(False)
        self.chooseTargetDropDown.setEnabled_(False)
        self.chooseWorkflowDropDown.setEnabled_(False)
        self.enableWorkflowDescriptionView_(False)
        self.runWorkflowButton.setEnabled_(False)
        self.cancelAndRestartButton.setEnabled_(False)

    def enableWorkflowViewControls(self):
        self.reloadWorkflowsButton.setEnabled_(True)
        self.reloadWorkflowsMenuItem.setEnabled_(True)
        self.cancelAndRestartButton.setEnabled_(True)
        self.chooseWorkflowLabel.setEnabled_(True)
        self.chooseTargetDropDown.setEnabled_(True)
        self.chooseWorkflowDropDown.setEnabled_(True)
        self.enableWorkflowDescriptionView_(True)
        self.runWorkflowButton.setEnabled_(True)
        self.cancelAndRestartButton.setEnabled_(True)

    @objc.IBAction
    def runWorkflow_(self, sender):
        '''Set up the selected workflow to run on secondary thread'''
        self.workflow_is_running = True
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

            # Show the computer name tab if needed. I hate waiting to put in the
            # name in DS.
            settingName = False
            for item in self.selectedWorkflow['components']:
                if item.get('type') == 'computer_name':
                    self.getComputerName_(item)
                    settingName = True
                    break
        if not settingName:
            self.workflowOnThreadPrep()

    def workflowOnThreadPrep(self):
        self.disableWorkflowViewControls()
        Utils.sendReport('in_progress', 'Preparing to run workflow %s...' % self.selectedWorkflow['name'])
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
        if self.selectedWorkflow:
            # count all of the workflow items - are we still using this?
            components = [item for item in self.selectedWorkflow['components']]
            component_count = len(components)

            self.should_update_volume_list = False

            for item in self.selectedWorkflow['components']:
                self.runComponent(item)
            if self.first_boot_items:
                # copy bits for first boot script
                packages_dir = os.path.join(self.targetVolume.mountpoint, 'usr/local/first-boot/')
                if not os.path.exists(packages_dir):
                    os.makedirs(packages_dir)
                Utils.copyFirstBoot(self.targetVolume.mountpoint)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.processWorkflowOnThreadComplete, None, YES)
        del pool

    def processWorkflowOnThreadComplete(self):
        '''Done running workflow, restart to imaged volume'''
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)
        self.workflow_is_running = False
        Utils.sendReport('success', 'Finished running %s.' % self.selectedWorkflow['name'])
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel(self.errorMessage)
        elif self.restartAction == 'restart' or self.restartAction == 'shutdown':
            self.restartToImagedVolume()
        else:
            if self.should_update_volume_list == True:
                NSLog("Refreshing volume list.")
                # again, this needs to be refactored
                self.volumes = macdisk.MountedVolumes()
                self.chooseTargetDropDown.removeAllItems()
                list = []
                for volume in self.volumes:
                    if volume.mountpoint != '/':
                        if volume.mountpoint.startswith("/Volumes"):
                            if volume.mountpoint != '/Volumes':
                                if volume.writable:
                                    list.append(volume.mountpoint)
                self.chooseTargetDropDown.addItemsWithTitles_(list)
                self.targetVolume = list[0]
                self.chooseTargetDropDown.selectItemWithTitle_(self.targetVolume)
            self.openEndWorkflowPanel()

    def runComponent(self, item):
        '''Run the selected workflow component'''
        # No point carrying on if something is broken
        if not self.errorMessage:
            self.counter = self.counter + 1.0
            # Restore image
            if item.get('type') == 'image' and item.get('url'):
                Utils.sendReport('in_progress', 'Restoring DMG: %s' % item.get('url'))
                self.Clone(item.get('url'), self.targetVolume)
            # Download and install package
            elif item.get('type') == 'package' and not item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Downloading and installing package(s): %s' % item.get('url'))
                self.downloadAndInstallPackages(item)
            # Download and copy package
            elif item.get('type') == 'package' and item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Downloading and installing first boot package(s): %s' % item.get('url'))
                self.downloadAndCopyPackage(item, self.counter)
                self.first_boot_items = True
            # Copy first boot script
            elif item.get('type') == 'script' and item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Copying first boot script %s' % str(self.counter))
                if item.get('url'):
                    if item.get('additional_headers'):
                        self.copyFirstBootScript(Utils.downloadFile(item.get('url'), item.get('additional_headers')), self.counter)
                    else:
                        self.copyFirstBootScript(Utils.downloadFile(item.get('url')), self.counter)
                else:
                    self.copyFirstBootScript(item.get('content'), self.counter)
                self.first_boot_items = True
            # Run script
            elif item.get('type') == 'script' and not item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Running script %s' % str(self.counter))
                if item.get('url'):
                    if item.get('additional_headers'):
                        self.runPreFirstBootScript(Utils.downloadFile(item.get('url'), item.get('additional_headers')), self.counter)
                    else:
                        self.runPreFirstBootScript(Utils.downloadFile(item.get('url')), self.counter)
                else:
                    self.runPreFirstBootScript(item.get('content'), self.counter)
            # Partition a disk
            elif item.get('type') == 'partition':
                Utils.sendReport('in_progress', 'Running partiton task.')
                self.partitionTargetDisk(item.get('partitions'), item.get('map'))
                if self.future_target == False:
                    # If a partition task is done without a new target specified, no other tasks can be parsed.
                    # Another workflow must be selected.
                    NSLog("No target specified, reverting to workflow selection screen.")

            elif item.get('type') == 'included_workflow':
                Utils.sendReport('in_progress', 'Running included workflow.')
                self.runIncludedWorkflow(item)

            # Format a volume
            elif item.get('type') == 'eraseVolume':
                Utils.sendReport('in_progress', 'Erasing volume with name %s' % item.get('name', 'Macintosh HD'))
                self.eraseTargetVolume(item.get('name', 'Macintosh HD'), item.get('format', 'Journaled HFS+'))
            elif item.get('type') == 'computer_name':
                if self.computerName:
                    Utils.sendReport('in_progress', 'Setting computer name to %s' % self.computerName)
                    script_dir = os.path.dirname(os.path.realpath(__file__))
                    with open(os.path.join(script_dir, 'set_computer_name.sh')) as script:
                        script=script.read()
                    self.copyFirstBootScript(script, self.counter)
                    self.first_boot_items = True
            else:
                Utils.sendReport('error', 'Found an unknown workflow item.')
                self.errorMessage = "Found an unknown workflow item."

    def runIncludedWorkflow(self, item):
        '''Runs an included workflow'''
        # find the workflow we're looking for
        progress_method = self.updateProgressTitle_Percent_Detail_
        #progress_method = None
        target_workflow = None
        included_workflow = None
        if 'script' in item:
            if progress_method:
                progress_method("Running script to determine included workflow...", -1, '')
            script = Utils.replacePlaceholders(item['script'], self.targetVolume.mountpoint)
            script_file = tempfile.NamedTemporaryFile(delete=False)
            script_file.write(script)
            script_file.close()
            os.chmod(script_file.name, 0700)
            proc = subprocess.Popen(script_file.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

            # while proc.poll() is None:
            #     output = proc.stdout.readline().strip().decode('UTF-8')
            #     if progress_method:
            #         progress_method(None, None, output)
            (out, err) = proc.communicate()
            if proc.returncode != 0:
                if err == None:
                    err = 'Unknown'
                Utils.sendReport('error', 'Could not run included workflow script: %s' % err)
                self.errorMessage = 'Could not run included workflow script: %s' % err
                return
            else:
                for line in out.splitlines():
                    if line.startswith("ImagrIncludedWorkflow: ") or line.startswith("ImagrIncludedWorkflow:"):
                        included_workflow = line.replace("ImagrIncludedWorkflow: ", "").replace("ImagrIncludedWorkflow:", "").strip()
                        break
        else:
            included_workflow = item['name']
        if included_workflow:
            for workflow in self.workflows:
                if included_workflow.strip() == workflow['name'].strip():
                    target_workflow = workflow
                    break
        # run the workflow
        if target_workflow:
            for component in target_workflow['components']:
                self.runComponent(component)
        else:
            Utils.sendReport('error', 'Could not find included workflow %s' % included_workflow)
            self.errorMessage = 'Could not find included workflow %s' % included_workflow

    def getComputerName_(self, component):
        auto_run = component.get('auto', False)
        hardware_info = Utils.get_hardware_info()

        # Try to get existing HostName
        try:
            preferencePath = os.path.join(self.targetVolume.mountpoint,'Library/Preferences/SystemConfiguration/preferences.plist')
            preferencePlist = FoundationPlist.readPlist(preferencePath)
            existing_name = preferencePlist['System']['System']['HostName']
        except:
            # If we can't get the name, assign empty string for now
            existing_name = ''

        if auto_run:
            if component.get('use_serial', False):
                self.computerName = hardware_info.get('serial_number', 'UNKNOWN')
            else:
                self.computerName = existing_name
            self.theTabView.selectTabViewItem_(self.mainTab)
            self.workflowOnThreadPrep()
        else:
            if component.get('use_serial', False):
                self.computerNameInput.setStringValue_(hardware_info.get('serial_number', ''))
            elif component.get('prefix', None):
                self.computerNameInput.setStringValue_(component.get('prefix'))
            else:
                self.computerNameInput.setStringValue_(existing_name)

            # Switch to the computer name tab
            self.theTabView.selectTabViewItem_(self.computerNameTab)
            self.mainWindow.makeFirstResponder_(self.computerNameInput)

    @objc.IBAction
    def setComputerName_(self, sender):
        self.computerName = self.computerNameInput.stringValue()
        self.theTabView.selectTabViewItem_(self.mainTab)
        self.workflowOnThreadPrep()

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

        if isinstance(self.targetVolume, macdisk.Disk):
            target_ref = "/dev/%s" % self.targetVolume.deviceidentifier
        else:
            raise macdisk.MacDiskError("target is not a Disk object")

        command = ["/usr/sbin/asr", "restore", "--source", str(source),
                   "--target", target_ref, "--noprompt", "--puppetstrings"]

        if erase:
            # check we can unmount the target... may as well fail here than later.
            if self.targetVolume.Mounted():
                self.targetVolume.Unmount()
            command.append("--erase")

        if not verify:
            command.append("--noverify")

        self.updateProgressTitle_Percent_Detail_('Restoring %s' % source, -1, '')
        NSLog("%@", str(command))
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
            self.errorMessage = "Cloning Error: %s" % stderr
            self.targetVolume.EnsureMountedWithRefresh()
            return False
        if task.poll() == 0:
            return True

    def downloadAndInstallPackages(self, item):
        url = item.get('url')
        custom_headers = item.get('additional_headers')
        self.updateProgressTitle_Percent_Detail_('Installing packages...', -1, '')
        # mount the target
        NSLog("%@", self.targetVolume.mountpoint)
        if not self.targetVolume.Mounted():
            self.targetVolume.Mount()

        package_name = os.path.basename(url)
        self.downloadAndInstallPackage(
            url, self.targetVolume.mountpoint,
            progress_method=self.updateProgressTitle_Percent_Detail_,
            additional_headers=custom_headers)

    def downloadAndInstallPackage(self, url, target, progress_method=None, additional_headers=None):
        if not os.path.basename(url).endswith('.pkg') and not os.path.basename(url).endswith('.dmg'):
            self.errorMessage = "%s doesn't end with either '.pkg' or '.dmg'" % url
            return False
        if os.path.basename(url).endswith('.dmg'):
            error = None
            # We're going to mount the dmg
            try:
                dmgmountpoints = Utils.mountdmg(url)
                dmgmountpoint = dmgmountpoints[0]
            except:
                self.errorMessage = "Couldn't mount %s" % url
                return False

            # Now we're going to go over everything that ends .pkg or
            # .mpkg and install it
            for package in os.listdir(dmgmountpoint):
                if package.endswith('.pkg') or package.endswith('.mpkg'):
                    pkg = os.path.join(dmgmountpoint, package)
                    retcode = self.installPkg(pkg, target, progress_method=progress_method)
                    if retcode != 0:
                        self.errorMessage = "Couldn't install %s" % pkg
                        return False

            # Unmount it
            try:
                Utils.unmountdmg(dmgmountpoint)
            except:
                self.errorMessage = "Couldn't unmount %s" % dmgmountpoint
                return False

        if os.path.basename(url).endswith('.pkg'):

            # Make our temp directory on the target
            temp_dir = tempfile.mkdtemp(dir=target)
            # Download it
            packagename = os.path.basename(url)
            (downloaded_file, error) = Utils.downloadChunks(url, os.path.join(temp_dir,
            packagename), additional_headers=additional_headers)
            if error:
                self.errorMessage = "Couldn't download - %s %s" % (url, error)
                return False
            # Install it
            retcode = self.installPkg(downloaded_file, target, progress_method=progress_method)
            if retcode != 0:
                self.errorMessage = "Couldn't install %s" % pkg
                return False
            # Clean up after ourselves
            shutil.rmtree(temp_dir)

    def downloadAndCopyPackage(self, item, counter):
        self.updateProgressTitle_Percent_Detail_(
            'Copying packages for install on first boot...', -1, '')
        # mount the target
        if not self.targetVolume.Mounted():
            self.targetVolume.Mount()
        url = item.get('url')
        custom_headers = item.get('additional_headers')
        package_name = os.path.basename(url)
        (output, error) = self.downloadPackage(url, self.targetVolume.mountpoint, counter,
                              progress_method=self.updateProgressTitle_Percent_Detail_, additional_headers=custom_headers)
        if error:
            self.errorMessage = "Error copying first boot package %s - %s" % (url, error)
            return False



    def downloadPackage(self, url, target, number, progress_method=None, additional_headers=None):
        error = None
        dest_dir = os.path.join(target, 'usr/local/first-boot/items')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        if not os.path.basename(url).endswith('.pkg') and not os.path.basename(url).endswith('.dmg'):
            error = "%s doesn't end with either '.pkg' or '.dmg'" % url
            return False, error
        if os.path.basename(url).endswith('.dmg'):
            NSLog("Copying pkg(s) from %@", url)
            (output, error) = self.copyPkgFromDmg(url, dest_dir, number)
        else:
            NSLog("Downloading pkg %@", url)
            package_name = "%03d-%s" % (number, os.path.basename(url))
            os.umask(0002)
            file = os.path.join(dest_dir, package_name)
            (output, error) = Utils.downloadChunks(url, file, progress_method=progress_method, additional_headers=additional_headers)

        return output, error

    def copyPkgFromDmg(self, url, dest_dir, number):
        error = None
        # We're going to mount the dmg
        try:
            dmgmountpoints = Utils.mountdmg(url)
            dmgmountpoint = dmgmountpoints[0]
        except:
            self.errorMessage = "Couldn't mount %s" % url
            return False

        # Now we're going to go over everything that ends .pkg or
        # .mpkg and install it
        pkg_list = []
        for package in os.listdir(dmgmountpoint):
            if package.endswith('.pkg') or package.endswith('.mpkg'):
                pkg = os.path.join(dmgmountpoint, package)
                dest_file = os.path.join(dest_dir, "%03d-%s" % (number, os.path.basename(pkg)))
                try:
                    if os.path.isfile(pkg):
                        shutil.copy(pkg, dest_file)
                    else:
                        shutil.copytree(pkg, dest_file)
                except:
                    error = "Couldn't copy %s" % pkg
                    return None, error
                pkg_list.append(dest_file)

        # Unmount it
        try:
            Utils.unmountdmg(dmgmountpoint)
        except:
            self.errorMessage = "Couldn't unmount %s" % dmgmountpoint
            return False, self.errorMessage

        return pkg_list, None

    def copyFirstBootScript(self, script, counter):
        if not self.targetVolume.Mounted():
            self.targetVolume.Mount()

        try:
            self.copyScript(
                script, self.targetVolume.mountpoint, counter,
                progress_method=self.updateProgressTitle_Percent_Detail_)
        except:
            self.errorMessage = "Couldn't copy script %s" % str(counter)
            return False

    def runPreFirstBootScript(self, script, counter):
        self.updateProgressTitle_Percent_Detail_(
            'Preparing to run scripts...', -1, '')
        # mount the target
        if not self.targetVolume.Mounted():
            self.targetVolume.Mount()

        retcode = self.runScript(
            script, self.targetVolume.mountpoint,
            progress_method=self.updateProgressTitle_Percent_Detail_)

        if retcode != 0:
            self.errorMessage = "Script %s returned a non-0 exit code" % str(int(counter))

    def runScript(self, script, target, progress_method=None):
        """
        Replaces placeholders in a script and then runs it.
        """
        # replace the placeholders in the script
        script = Utils.replacePlaceholders(script, target)

        # Copy script content to a temporary location and make executable
        script_file = tempfile.NamedTemporaryFile(delete=False)
        script_file.write(script)
        script_file.close()
        os.chmod(script_file.name, 0700)
        if progress_method:
            progress_method("Running script...", -1, '')
        proc = subprocess.Popen(script_file.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        while proc.poll() is None:
            output = proc.stdout.readline().strip().decode('UTF-8')
            if progress_method:
                progress_method(None, None, output)
        os.remove(script_file.name)
        return proc.returncode

    def copyScript(self, script, target, number, progress_method=None):
        """
        Copies a
         script to a specific volume
        """
        dest_dir = os.path.join(target, 'usr/local/first-boot/items')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        dest_file = os.path.join(dest_dir, "%03d" % number)
        if progress_method:
            progress_method("Copying script to %s" % dest_file, 0, '')
        # convert placeholders
        if self.computerName:
            script = Utils.replacePlaceholders(script, target, self.computerName)
        else:
            script = Utils.replacePlaceholders(script, target)
        # write file
        with open(dest_file, "w") as text_file:
            text_file.write(script)
        # make executable
        os.chmod(dest_file, 0755)
        return dest_file

    @objc.IBAction
    def restartButtonClicked_(self, sender):
        NSLog("Restart Button Clicked")
        self.restartToImagedVolume()

    def restartToImagedVolume(self):
        # set the startup disk to the restored volume
        if self.blessTarget == True:
            try:
                self.targetVolume.SetStartupDisk()
            except:
                for volume in self.volumes:
                    if str(volume.mountpoint) == str(self.targetVolume):
                        volume.SetStartupDisk()

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
            # NSLog("You clicked %@ - shutdown", returncode)
            self.restartAction = 'shutdown'
            self.restartToImagedVolume()
        elif returncode == 1:
            # NSLog("You clicked %@ - restart", returncode)
            self.restartAction = 'restart'
            self.restartToImagedVolume()
        elif returncode == 0:
            # NSLog("You clicked %@ - another workflow", returncode)
            self.enableWorkflowViewControls()
            self.chooseImagingTarget_(contextinfo)

    def enableAllButtons_(self, sender):
        self.cancelAndRestartButton.setEnabled_(True)
        self.runWorkflowButton.setEnabled_(True)

    def disableAllButtons_(self, sender):
        self.cancelAndRestartButton.setEnabled_(False)
        self.runWorkflowButton.setEnabled_(False)

    @objc.IBAction
    def runUtilityFromMenu_(self, sender):
        app_name = sender.title()
        app_path = os.path.join('/Applications/Utilities/', app_name + '.app')
        if os.path.exists(app_path):
            Utils.launchApp(app_path)

    def buildUtilitiesMenu(self):
        """
        Adds all applications in /Applications/Utilities to the Utilities menu
        """
        self.utilities_menu.removeAllItems()
        for item in os.listdir('/Applications/Utilities'):
            if item.endswith('.app'):
                item_name = os.path.splitext(item)[0]
                new_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                    item_name, self.runUtilityFromMenu_, u'')
                new_item.setTarget_(self)
                self.utilities_menu.addItem_(new_item)

    def installPkg(self, pkg, target, progress_method=None):
        """
        Installs a package on a specific volume
        """
        NSLog("Installing %@ to %@", pkg, target)
        if progress_method:
            progress_method("Installing %s" % os.path.basename(pkg), 0, '')
        cmd = ['/usr/sbin/installer', '-pkg', pkg, '-target', target, '-verboseR']
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        while proc.poll() is None:
            output = proc.stdout.readline().strip().decode('UTF-8')
            if output.startswith("installer:"):
                msg = output[10:].rstrip("\n")
                if msg.startswith("PHASE:"):
                    phase = msg[6:]
                    if phase:
                        NSLog(phase)
                        if progress_method:
                            progress_method(None, None, phase)
                elif msg.startswith("STATUS:"):
                    status = msg[7:]
                    if status:
                        NSLog(status)
                        if progress_method:
                            progress_method(None, None, status)
                elif msg.startswith("%"):
                    percent = float(msg[1:])
                    NSLog("%@ percent complete", percent)
                    if progress_method:
                        progress_method(None, percent, None)
                elif msg.startswith(" Error"):
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)
                elif msg.startswith(" Cannot install"):
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)
                else:
                    NSLog(msg)
                    if progress_method:
                        progress_method(None, None, msg)

        return proc.returncode

    def partitionTargetDisk(self, partitions=None, partition_map="GPTFormat", progress_method=None):
        """
        Formats a target disk according to specifications.
        'partitions' is a list of dictionaries of partition mappings for names, sizes, formats.
        'partition_map' is a volume map type - MBR, GPT, or APM.
        """
        # self.targetVolume.mountpoint should be the actual volume we're targeting.
        # self.targetVolume is the macdisk object that can be queried for its parent disk
        parent_disk = self.targetVolume.Info()['ParentWholeDisk']
        NSLog("Parent disk: %@", parent_disk)

        numPartitions = 0
        cmd = ['/usr/sbin/diskutil', 'partitionDisk', '/dev/' + parent_disk]
        partitionCmdList = list()
        future_target_name = ''
        self.future_target = False
        if partitions:
            # A partition map was provided, so use that to repartition the disk
            for partition in partitions:
                target = list()
                # Default format type is "Journaled HFS+, case-insensitive"
                target.append(partition.get('format_type', 'Journaled HFS+'))
                # Default name is "Macintosh HD"
                target.append(partition.get('name', 'Macintosh HD'))
                # Default partition size is 100% of the disk size
                target.append(partition.get('size', '100%'))
                partitionCmdList.extend(target)
                numPartitions += 1
                if partition.get('target'):
                    NSLog("New target action found.")
                    # A new default target for future workflow actions was specified
                    self.future_target = True
                    future_target_name = partition.get('name', 'Macintosh HD')
            cmd.append(str(numPartitions))
            cmd.append(str(partition_map))
            cmd.extend(partitionCmdList)
        else:
            # No partition list was provided, so we just partition the target disk
            # with one volume, named 'Macintosh HD', using JHFS+, GPT Format
            cmd = ['/usr/sbin/diskutil', 'partitionDisk', '/dev/' + parent_disk,
                    '1', 'GPTFormat', 'Journaled HFS+', 'Macintosh HD', '100%']
        NSLog("%@", str(cmd))
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (partOut, partErr) = proc.communicate()
        if partErr:
            NSLog("Error occurred: %@", partErr)
            self.errorMessage = partErr
        NSLog("%@", partOut)
        # At this point, we need to reload the possible targets, because '/Volumes/Macintosh HD' might not exist
        self.should_update_volume_list = True
        if self.future_target == True:
            # Now assign self.targetVolume to new mountpoint
            partitionListFromDisk = macdisk.Disk('/dev/' + str(parent_disk))
            # this is in desperate need of refactoring and rewriting
            # the only way to safely set self.targetVolume is to assign a new macdisk.Disk() object
            # and then find the partition that matches our target
            for partition in partitionListFromDisk.Partitions():
                if partition.Info()['MountPoint'] == cmd[6]:
                    self.targetVolume = partition
                    break
            NSLog("New target volume mountpoint is %@", self.targetVolume.mountpoint)


    def eraseTargetVolume(self, name='Macintosh HD', format='Journaled HFS+', progress_method=None):
        """
        Erases the target volume.
        'name' can be used to rename the volume on reformat.
        'format' can be used to specify a format type.
        If no options are provided, it will format the volume with name 'Macintosh HD' with JHFS+.
        """
        cmd = ['/usr/sbin/diskutil', 'eraseVolume', format, name, self.targetVolume.mountpoint ]
        NSLog("%@", cmd)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (eraseOut, eraseErr) = proc.communicate()
        if eraseErr:
            NSLog("Error occured when erasing volume: %@", eraseErr)
            self.errorMessage = eraseErr
        NSLog("%@", eraseOut)
        # Reload possible targets, because '/Volumes/Macintosh HD' might not exist
        if name != 'Macintosh HD':
            # If the volume was renamed, or isn't named 'Macintosh HD', then we should recheck the volume list
            self.should_update_volume_list = True


    def shakeWindow(self):
        shake = {'count': 1, 'duration': 0.3, 'vigor': 0.04}
        shakeAnim = Quartz.CAKeyframeAnimation.animation()
        shakePath = Quartz.CGPathCreateMutable()
        frame = self.mainWindow.frame()
        Quartz.CGPathMoveToPoint(shakePath, None, NSMinX(frame), NSMinY(frame))
        shakeLeft = NSMinX(frame) - frame.size.width * shake['vigor']
        shakeRight = NSMinX(frame) + frame.size.width * shake['vigor']
        for i in range(shake['count']):
            Quartz.CGPathAddLineToPoint(shakePath, None, shakeLeft, NSMinY(frame))
            Quartz.CGPathAddLineToPoint(shakePath, None, shakeRight, NSMinY(frame))
            Quartz.CGPathCloseSubpath(shakePath)
        shakeAnim._['path'] = shakePath
        shakeAnim._['duration'] = shake['duration']
        self.mainWindow.setAnimations_(NSDictionary.dictionaryWithObject_forKey_(shakeAnim, "frameOrigin"))
        self.mainWindow.animator().setFrameOrigin_(frame.origin)

    @objc.IBAction
    def showHelp_(self, sender):
        NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_("https://github.com/grahamgilbert/imagr/wiki"))
