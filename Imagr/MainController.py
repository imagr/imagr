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
from Quartz.CoreGraphics import *
import random
import subprocess
import sys
import macdisk
import urllib2
import Utils
import PyObjCTools
import tempfile
import shutil
import Quartz
import time
import urlparse
import powermgr
import osinstall
import signal
import unicodedata
import powermgr
class MainController(NSObject):
    objc.setVerbose(1)
    mainWindow = objc.IBOutlet()
    backgroundWindow = objc.IBOutlet()

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

    variablePanel = objc.IBOutlet()
    variablePanelLabel = objc.IBOutlet()
    variablePanelValue = objc.IBOutlet()

    authenticationPanel = objc.IBOutlet()
    authenticationPanelUsernameField = objc.IBOutlet()
    authenticationPanelPasswordField = objc.IBOutlet()

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

    countdownWarningImage = objc.IBOutlet()
    countdownCancelButton = objc.IBOutlet()

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
    waitForNetwork = True
    firstBootReboot = True
    autoRunTime = 30
    autorunWorkflow = None
    cancelledAutorun = False
    authenticatedUsername = None
    authenticatedPassword = None
    target_volume_name = None
    variablesArray = []
    environmentVariableArray = []

    # For localize script
    keyboard_layout_name = None
    keyboard_layout_id = None
    language = None
    locale = None
    timezone = None

    def errorPanel_(self, error):
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

    def errorNotificationPanel_(self, error):
        if error:
            errorText = str(error)
        else:
            errorText = "Unknown error"

        # Send a report to the URL if it's configured
        Utils.sendReport('error', errorText)

        self.alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
            NSLocalizedString(errorText.decode('utf8'), None),
            NSLocalizedString(u"OK", None),
            NSLocalizedString(u"", None),
            objc.nil,
            NSLocalizedString(u"", None))

        self.errorMessage = None
        self.alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.mainWindow, self, None, objc.nil)

    @objc.python_method
    def receiveSignal(self,signalNumber, frame):
        NSLog("startosinstall prepare phase complete")
        Utils.sendReport('in_progress', 'startosinstall prepare phase complete')
        return

    def runStartupTasks(self):
        signal.signal(signal.SIGUSR1, self.receiveSignal)

        if self.backgroundWindowSetting() == u"always":
            self.showBackgroundWindow()

        self.mainWindow.center()
        self.mainWindow.setCanBecomeVisibleWithoutLogin_(True)
        # Run app startup - get the images, password, volumes - anything that takes a while
        self.progressText.setStringValue_("Application Starting...")
        self.chooseWorkflowDropDown.removeAllItems()
        self.progressIndicator.setIndeterminate_(True)
        self.progressIndicator.setUsesThreadedAnimation_(True)
        self.progressIndicator.startAnimation_(self)
        self.registerForWorkspaceNotifications()
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    def backgroundWindowSetting(self):
        return Utils.getPlistData(u"background_window") or u"auto"

    def showBackgroundWindow(self):
        # Create a background window that covers the whole screen.
        NSLog(u"Showing background window")
        rect = NSScreen.mainScreen().frame()
        self.backgroundWindow.setCanBecomeVisibleWithoutLogin_(True)
        self.backgroundWindow.setFrame_display_(rect, True)
        backgroundColor = NSColor.darkGrayColor()
        self.backgroundWindow.setBackgroundColor_(backgroundColor)
        self.backgroundWindow.setOpaque_(False)
        self.backgroundWindow.setIgnoresMouseEvents_(False)
        self.backgroundWindow.setAlphaValue_(1.0)
        self.backgroundWindow.orderFrontRegardless()
        self.backgroundWindow.setLevel_(kCGNormalWindowLevel - 1)
        self.backgroundWindow.setCollectionBehavior_(NSWindowCollectionBehaviorStationary | NSWindowCollectionBehaviorCanJoinAllSpaces)

    def loadBackgroundImage_(self, urlString):
        if self.backgroundWindowSetting() == u"never":
            return
        NSLog(u"Loading background image")
        if self.backgroundWindowSetting() == u"auto":
            runningApps = [x.bundleIdentifier() for x in NSWorkspace.sharedWorkspace().runningApplications()]
            if u"com.apple.dock" not in runningApps:
                self.performSelectorOnMainThread_withObject_waitUntilDone_(
                    self.showBackgroundWindow, None, YES)
            else:
                NSLog(u"Not showing background window as Dock.app is running")
                return

        def gcd(a, b):
            """Return greatest common divisor of two numbers"""
            if b == 0:
                return a
            return gcd(b, a % b)

        if not urlString.endswith(u"?"):
            try:
                verplist = FoundationPlist.readPlist("/System/Library/CoreServices/SystemVersion.plist")
                osver = verplist[u"ProductUserVisibleVersion"]
                osbuild = verplist[u"ProductBuildVersion"]
                size = NSScreen.mainScreen().frame().size
                w = int(size.width)
                h = int(size.height)
                divisor = gcd(w, h)
                aw = w / divisor
                ah = h / divisor
                urlString += u"?osver=%s&osbuild=%s&w=%d&h=%d&a=%d-%d" % (osver, osbuild, w, h, aw, ah)
            except:
                pass
        url = NSURL.URLWithString_(urlString)
        image = NSImage.alloc().initWithContentsOfURL_(url)
        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.setBackgroundImage_, image, YES)

    def setBackgroundImage_(self, image):
        self.backgroundWindow.contentView().setWantsLayer_(True)
        self.backgroundWindow.contentView().layer().setContents_(image)

    def registerForWorkspaceNotifications(self):
        nc = NSWorkspace.sharedWorkspace().notificationCenter()
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived_, NSWorkspaceDidMountNotification, None)
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived_, NSWorkspaceDidUnmountNotification, None)
        nc.addObserver_selector_name_object_(
            self, self.wsNotificationReceived_, NSWorkspaceDidRenameVolumeNotification, None)

    def wsNotificationReceived_(self, notification):
        if self.workflow_is_running:
            self.should_update_volume_list = True
            return
        notification_name = notification.name()
        user_info = notification.userInfo()
        if notification_name == NSWorkspaceDidMountNotification:
            new_volume = user_info['NSDevicePath']
        elif notification_name == NSWorkspaceDidUnmountNotification:
            removed_volume = user_info['NSDevicePath']
        elif notification_name == NSWorkspaceDidRenameVolumeNotification:
            pass
        self.reloadVolumes()

    def validTargetVolumes(self):
        volume_list = []
        for volume in self.volumes:
            if volume.mountpoint != '/':
                if volume.mountpoint.startswith("/Volumes/") or volume.filevault :
                    if volume.writable:
                        volume_list.append(volume.mountpoint)
        return volume_list

    def reloadVolumes(self):
        if self.targetVolume._attributes['FilesystemType'] == 'apfs':
            self.targetVolume=Utils.system_volume(self.targetVolume)
            if not self.targetVolume.Mounted():
                self.targetVolume.Mount()
        self.volumes = Utils.available_volumes()
        self.chooseTargetDropDown.removeAllItems()
        volume_list = self.validTargetVolumes()
        self.chooseTargetDropDown.addItemsWithTitles_(volume_list)
        # reselect previously selected target if possible
        if self.targetVolume:
            self.chooseTargetDropDown.selectItemWithTitle_(self.targetVolume.mountpoint)
            selected_volume = self.chooseTargetDropDown.titleOfSelectedItem()
        else:
            if self.target_volume_name:
                selected_volume = self.target_volume_name
            else:
                selected_volume = volume_list[0]
            self.chooseTargetDropDown.selectItemWithTitle_(selected_volume)
        for volume in self.volumes:
            if volume.mountpoint and str(volume.mountpoint.encode('utf8')) == str(selected_volume.encode('utf8')):
                self.targetVolume = volume

    def expandImagingProgressPanel(self):
        self.imagingProgressPanel.setContentSize_(NSSize(466, 119))
        self.countdownWarningImage.setHidden_(False)
        self.countdownCancelButton.setHidden_(False)
        self.imagingLabel.setFrameOrigin_(NSPoint(89, 87))
        self.imagingLabel.setFrameSize_(NSSize(359, 17))
        self.imagingProgress.setFrameOrigin_(NSPoint(91, 60))
        self.imagingProgress.setFrameSize_(NSSize(355, 20))
        self.imagingProgressDetail.setFrameOrigin_(NSPoint(89, 41))
        self.imagingProgressDetail.setFrameSize_(NSSize(360, 17))

    def contractImagingProgressPanel(self):
        self.imagingProgressPanel.setContentSize_(NSSize(466, 98))
        self.countdownWarningImage.setHidden_(True)
        self.countdownCancelButton.setHidden_(True)
        self.imagingLabel.setFrameOrigin_(NSPoint(17, 66))
        self.imagingLabel.setFrameSize_(NSSize(431, 17))
        self.imagingProgress.setFrameOrigin_(NSPoint(20, 39))
        self.imagingProgress.setFrameSize_(NSSize(426, 20))
        self.imagingProgressDetail.setFrameOrigin_(NSPoint(18, 20))
        self.imagingProgressDetail.setFrameSize_(NSSize(431, 17))


    @objc.IBAction
    def endVariablePanel_(self, sender):
        '''Called when user clicks 'OK' in the variable panel'''
        # store the username and password
        NSApp.endSheet_(self.variablePanel)

        self.environmentVariableArray.append({self.variablesArray[0].keys()[0]:self.variablePanelValue.stringValue()})


        self.variablePanel.orderOut_(self)
        self.variablesArray.pop(0)

        if (self.variablesArray):
            self.variablePanelLabel.setStringValue_(self.variablesArray[0].values()[0])
            self.variablePanelValue.setStringValue_("")
            NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
                                                                                      self.variablePanel, self.mainWindow, self, None, None)
        else:
            self.workflowOnThreadPrep()


    def showAuthenticationPanel(self):
        '''Show the authentication panel'''
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.authenticationPanel, self.mainWindow, self, None, None)

    @objc.IBAction
    def cancelAuthenticationPanel_(self, sender):
        '''Called when user clicks 'Quit' in the authentication panel'''
        NSApp.endSheet_(self.authenticationPanel)
        NSApp.terminate_(self)

    @objc.IBAction
    def endAuthenticationPanel_(self, sender):
        '''Called when user clicks 'Continue' in the authentication panel'''
        # store the username and password
        self.authenticatedUsername = self.authenticationPanelUsernameField.stringValue()
        self.authenticatedPassword = self.authenticationPanelPasswordField.stringValue()
        NSApp.endSheet_(self.authenticationPanel)
        self.authenticationPanel.orderOut_(self)
        # re-request the workflows.plist, this time with username and password available
        NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadData, self, None)

    def loadData(self):
        pool = NSAutoreleasePool.alloc().init()
        self.buildUtilitiesMenu()
        self.volumes = Utils.available_volumes()


#        self.volumes = Utils.mountedVolumes()
        theURL = Utils.getServerURL()

        if theURL:
            plistData = None
            tries = 0
            while (not plistData) and (tries < 3):
                tries += 1
                (plistData, error) = Utils.downloadFile(
                    theURL, username=self.authenticatedUsername, password=self.authenticatedPassword)
                if error:
                    try:
                        if error.reason[0] in [401, -1012, -1013]:
                            # 401:   HTTP status code: authentication required
                            # -1012: NSURLErrorDomain code "User cancelled authentication" -- returned
                            #        when we try a given name and password and fail
                            # -1013: NSURLErrorDomain code "User Authentication Required"
                            NSLog("Configuration plist requires authentication.")
                            # show authentication panel using the main thread
                            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                                self.showAuthenticationPanel, None, YES)
                            del pool
                            return
                        elif error.reason[0] < 0:
                            NSLog("Failed to load configuration plist: %@", repr(error.reason))
                            # Possibly ssl error due to a bad clock, try setting the time.
                            Utils.setDate()
                    except AttributeError, IndexError:
                        pass

            if plistData:
                plistData = plistData.replace("{{current_volume_path}}", Utils.currentVolumePath().encode("utf8"))
                try:
                    converted_plist = FoundationPlist.readPlistFromString(plistData)
                except:
                    self.errorMessage = "Configuration plist couldn't be read."

                try:
                    self.waitForNetwork = converted_plist['wait_for_network']
                except:
                    pass

                try:
                    self.autoRunTime = converted_plist['autorun_time']
                except:
                    pass

                try:
                    urlString = converted_plist['background_image']
                    NSThread.detachNewThreadSelector_toTarget_withObject_(self.loadBackgroundImage_, self, urlString)
                except:
                    pass

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

                try:
                    self.autorunWorkflow = converted_plist['autorun']

                    # If we've already cancelled autorun, don't bother trying to autorun again.
                    if self.cancelledAutorun:
                        self.autorunWorkflow = None
                except:
                    pass

                try:
                    self.target_volume_name = urllib2.unquote(
                        converted_plist['target_volume_name'])
                    NSLog("Set target volume name as: %@", self.target_volume_name)
                except:
                    pass
            else:
                self.errorMessage = "Couldn't get configuration plist. \n %s. \n '%s'" % (error.reason, error.url)
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
            self.errorPanel_(self.errorMessage)
        else:
            if self.hasLoggedIn:
                self.enableWorkflowViewControls()
                self.theTabView.selectTabViewItem_(self.mainTab)
                self.chooseImagingTarget_(None)

                self.isAutorun()

            else:
                self.theTabView.selectTabViewItem_(self.loginTab)
                self.mainWindow.makeFirstResponder_(self.password)

    def isAutorun(self):
        if self.autorunWorkflow:
            self.countdownOnThreadPrep()

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

                self.isAutorun()

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
            volume_list = []
            for volume in self.volumes:
                volume_list.append(volume.mountpoint)

            # Let's add the items to the popup
            self.startupDiskDropdown.addItemsWithTitles_(volume_list)
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
        volume_list = self.validTargetVolumes()
         # No writable volumes, this is bad.
        if len(volume_list) == 0:
            alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                NSLocalizedString(u"No writable volumes found", None),
                NSLocalizedString(u"Restart", None),
                NSLocalizedString(u"Open Disk Utility", None),
                objc.nil,
                NSLocalizedString(u"No writable volumes were found on this Mac.", None))
            alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                self.mainWindow, self, self.noVolAlertDidEnd_returnCode_contextInfo_, objc.nil)
        else:
            self.chooseTargetDropDown.addItemsWithTitles_(volume_list)
            if self.targetVolume:
                self.chooseTargetDropDown.selectItemWithTitle_(self.targetVolume.mountpoint)

            if self.target_volume_name:
                try:
                    selected_volume = unicodedata.normalize("NFD", "/Volumes/%s" % self.target_volume_name)
                    volume_list.index(selected_volume) # Check if target volume is in list
                except ValueError:
                    self.errorMessage = "Could not find a volume with target name: %s" % self.target_volume_name.UTF8String()
                    NSLog(self.errorMessage.decode('utf8'))
                    self.autorunWorkflow = None
                    selected_volume = volume_list[0]
                    self.errorNotificationPanel_(self.errorMessage)

                self.chooseTargetDropDown.selectItemWithTitle_(selected_volume)
            else:
                selected_volume = self.chooseTargetDropDown.titleOfSelectedItem()

            for volume in self.volumes:
                if str(volume.mountpoint.encode('utf8')) == str(selected_volume.encode('utf8')):
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
            if str(volume.mountpoint.encode('utf8')) == str(volume_name.encode('utf8')):
                self.targetVolume = volume
                break


    @objc.IBAction
    def closeImagingTarget_(self, sender):
        self.enableAllButtons_(sender)
        NSApp.endSheet_(self.chooseTargetPanel)
        self.chooseTargetPanel.orderOut_(self)
        self.setStartupDisk_(sender)

    @objc.IBAction
    def selectWorkflow_(self, sender):
        self.chooseWorkflowDropDown.removeAllItems()
        workflow_list = []
        for workflow in self.workflows:
            if 'hidden' in workflow:
                # Don't add 'hidden' workflows to the list
                if workflow['hidden'] == False:
                    workflow_list.append(workflow['name'])
            else:
                # If not specified, assume visible
                workflow_list.append(workflow['name'])

        self.chooseWorkflowDropDown.addItemsWithTitles_(workflow_list)

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
            self.workflowDescription.setTextColor_(NSColor.disabledControlTextColor())

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
        NSLog(u"Preventing sleep...")
        powermgr.assertNoIdleSleep()
        selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()


        if self.autorunWorkflow:
            NSLog("running autorun workflow")
            runWorkflowNow()

        self.selectedWorkflow = None
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                self.selectedWorkflow = workflow
                break

        label_string = "Are you sure you want to run workflow %s?" % self.selectedWorkflow['name']

        alert = NSAlert.alertWithMessageText_defaultButton_alternateButton_otherButton_informativeTextWithFormat_(
                                                                                                                  NSLocalizedString(label_string, None),
                                                                                                                  NSLocalizedString(u"Run", None),
                                                                                                                  NSLocalizedString(u"Cancel", None),
                                                                                                                  NSLocalizedString(u"", None),
                                                                                                                  NSLocalizedString(u"", None),)

        alert.beginSheetModalForWindow_modalDelegate_didEndSelector_contextInfo_(
                                                                                                                                                                                           self.mainWindow, self, self.startWorkflowAlertDidEnd_returnCode_contextInfo_, objc.nil)
    def runWorkflowNow(self):
        '''Set up the selected workflow to run on secondary thread'''
        self.workflow_is_running = True

        # let's get the workflow
        if self.autorunWorkflow:
            selected_workflow = self.autorunWorkflow
        else:
            selected_workflow = self.chooseWorkflowDropDown.titleOfSelectedItem()
        self.selectedWorkflow = None
        for workflow in self.workflows:
            if selected_workflow == workflow['name']:
                self.selectedWorkflow = workflow
                break
        if self.selectedWorkflow:
            if 'restart_action' in self.selectedWorkflow:
                self.restartAction = self.selectedWorkflow['restart_action']
            if 'first_boot_reboot' in self.selectedWorkflow:
                self.firstBootReboot = self.selectedWorkflow['first_boot_reboot']
            if 'bless_target' in self.selectedWorkflow:
                self.blessTarget = self.selectedWorkflow['bless_target']
            else:
                self.blessTarget = True

            # Show the computer name tab if needed. I hate waiting to put in the
            # name in DS.
            settingName = False
            settingVariables = False
            variablesArray = []
            self.environmentVariableArray = []
            for item in self.selectedWorkflow['components']:
                if self.checkForVariablesNameComponent_(item):
                    self.variablesArray = item.get('variableLabels', [])
                    settingVariables=True
                    break

            for item in self.selectedWorkflow['components']:
                if self.checkForNameComponent_(item):
                    self.getComputerName_(item)
                    settingName = True
                    break

            if not settingName and settingVariables:
                self.getVariables()

            if not settingName and not settingVariables:
                self.workflowOnThreadPrep()

    def checkForNameComponent_(self, item):
        if item.get('type') == 'computer_name':
            return True
        if item.get('type') == 'included_workflow':
            included_workflow = self.getIncludedWorkflow_(item)
            for workflow in self.workflows:
                if workflow['name'] == included_workflow:
                    for new_item in workflow['components']:
                        if self.checkForNameComponent_(new_item):
                            return True

        return False

    def checkForVariablesNameComponent_(self, item):
        if item.get('type') == 'variables':
            return True
        if item.get('type') == 'included_workflow':
            included_workflow = self.getIncludedWorkflow_(item)
            for workflow in self.workflows:
                if workflow['name'] == included_workflow:
                    for new_item in workflow['components']:
                        if self.checkForNameComponent_(new_item):
                            return True

        return False

    @PyObjCTools.AppHelper.endSheetMethod
    def startWorkflowAlertDidEnd_returnCode_contextInfo_(self, alert, returncode, contextinfo):

        # 0 = Cancel
        # 1 = Run

        if returncode == 1:
            self.runWorkflowNow()
        elif returncode == 0:
            NSLog("Cancelling")

    def workflowOnThreadPrep(self):
        self.disableWorkflowViewControls()
        Utils.sendReport('in_progress', 'Preparing to run workflow %s...' % self.selectedWorkflow['name'].UTF8String())
        self.imagingLabel.setStringValue_("Preparing to run workflow...")
        self.imagingProgressDetail.setStringValue_('')
        self.contractImagingProgressPanel()
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.imagingProgressPanel, self.mainWindow, self, None, None)
        # initialize the progress bar
        self.imagingProgress.setMinValue_(0.0)
        self.imagingProgress.setMaxValue_(100.0)
        self.imagingProgress.setIndeterminate_(True)
        self.imagingProgress.setUsesThreadedAnimation_(True)
        self.imagingProgress.startAnimation_(self)

        NSThread.detachNewThreadSelector_toTarget_withObject_(
            self.processWorkflowOnThread_, self, None)

    def countdownOnThreadPrep(self):
        self.disableWorkflowViewControls()

        label_string = "Preparing to run %s on %s " % (self.autorunWorkflow,self.targetVolume.mountpoint)

        self.imagingLabel.setStringValue_(label_string)
        #self.imagingProgressDetail.setStringValue_('')
        self.expandImagingProgressPanel()
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
            self.imagingProgressPanel, self.mainWindow, self, None, None)
        # initialize the progress bar
        self.imagingProgress.setMinValue_(0.0)
        self.imagingProgress.setMaxValue_(self.autoRunTime)
        self.imagingProgress.setIndeterminate_(True)
        self.imagingProgress.setUsesThreadedAnimation_(True)
        self.imagingProgress.startAnimation_(self)
        NSThread.detachNewThreadSelector_toTarget_withObject_(
            self.processCountdownOnThread_, self, None)

    def processCountdownOnThread_(self, sender):
        '''Count down for 30s or admin provided'''
        countdown = self.autoRunTime
        #pool = NSAutoreleasePool.alloc().init()
        if self.autorunWorkflow and self.targetVolume:
            self.should_update_volume_list = False

            # Count down for 30s or admin provided.
            for remaining in range(countdown, 0, -1):
                if not self.autorunWorkflow:
                    break

                self.updateProgressTitle_Percent_Detail_(None, countdown - remaining, "Beginning in {}s".format(remaining))
                import time
                time.sleep(1)

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.processCountdownOnThreadComplete, None, YES)
        #del pool

    def processCountdownOnThreadComplete(self):
        '''Done running countdown, start the default workflow'''
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)

        # Make sure the user still wants to autorun the default workflow (i.e. hasn't clicked cancel).
        if self.autorunWorkflow:
            self.runWorkflowNow()

    @objc.IBAction
    def cancelCountdown_(self, sender):
        '''The user didn't want to automatically run the default workflow after all.'''
        self.autorunWorkflow = None
        # Avoid trying to autorun again.
        self.cancelledAutorun = True
        self.enableWorkflowViewControls()

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

    def setupFirstBootDir(self):
        first_boot_items_dir = os.path.join(self.targetVolume.mountpoint, 'private/var/.imagr/first-boot/items/')
        if not os.path.exists(first_boot_items_dir):
            os.makedirs(first_boot_items_dir, 0755)

    def setupFirstBootTools(self):
        # copy bits for first boot script
        packages_dir = os.path.join(
            self.targetVolume.mountpoint, 'private/var/.imagr/first-boot/')
        if not os.path.exists(packages_dir):
            self.setupFirstBootDir()
        Utils.copyFirstBoot(self.targetVolume.mountpoint,
                            self.waitForNetwork, self.firstBootReboot)

    def processWorkflowOnThread_(self, sender):
        '''Process the selected workflow'''
        pool = NSAutoreleasePool.alloc().init()
        if self.selectedWorkflow:
            # count all of the workflow items - are we still using this?
            components = [item for item in self.selectedWorkflow['components']]
            component_count = len(components)

            self.should_update_volume_list = False
            for item in self.selectedWorkflow['components']:
                if (item.get('type') == 'startosinstall' and
                        self.first_boot_items):
                    # we won't get a chance to do this after this component
                    self.setupFirstBootTools()
                self.runComponent_(item)
            if self.first_boot_items:
                self.setupFirstBootTools()

        self.performSelectorOnMainThread_withObject_waitUntilDone_(
            self.processWorkflowOnThreadComplete, None, YES)
        del pool

    def processWorkflowOnThreadComplete(self):
        '''Done running workflow, restart to imaged volume'''
        NSApp.endSheet_(self.imagingProgressPanel)
        self.imagingProgressPanel.orderOut_(self)
        self.workflow_is_running = False

        # Disable autorun so users are able to select additional workflows to run.
        self.autorunWorkflow = None

        Utils.sendReport('success', 'Finished running %s.' % self.selectedWorkflow['name'].UTF8String())

        # Bless the target if we need to
        if self.blessTarget == True:
            try:
                self.targetVolume=Utils.system_volume(self.targetVolume)
                self.targetVolume.SetStartupDisk()
            except:
                for volume in self.volumes:
                    if volume.mountpoint and str(volume.mountpoint.encode('utf8')) == str(self.targetVolume.mountpoint.encode('utf8')):
                        volume.SetStartupDisk()
        if self.errorMessage:
            self.theTabView.selectTabViewItem_(self.errorTab)
            self.errorPanel_(self.errorMessage)
        elif self.restartAction == 'restart' or self.restartAction == 'shutdown':
            self.restartToImagedVolume()
        else:
            if self.should_update_volume_list == True:
                NSLog("Refreshing volume list.")
                self.reloadVolumes()
            self.openEndWorkflowPanel()

    def runComponent_(self, item):
        '''Run the selected workflow component'''
        # No point carrying on if something is broken
        if not self.errorMessage:
            self.counter = self.counter + 1.0
            # Restore image
            if item.get('type') == 'image' and item.get('url'):
                Utils.sendReport('in_progress', 'Restoring DMG: %s' % item.get('url'))
                self.Clone(
                    item.get('url'),
                    self.targetVolume,
                    verify=item.get('verify', True),
                    ramdisk=item.get('ramdisk', False),
                )
            # startosinstall
            elif item.get('type') == 'startosinstall':
                Utils.sendReport('in_progress', 'starting macOS install: %s' % item.get('url'))
                self.startOSinstall(item, ramdisk=item.get('ramdisk', False))
            # Download and install package
            elif item.get('type') == 'package' and not item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Downloading and installing package(s): %s' % item.get('url'))
                self.downloadAndInstallPackages_(item)
            # Download and copy package
            elif item.get('type') == 'package' and item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Downloading and installing first boot package(s): %s' % item.get('url'))
                self.downloadAndCopyPackage(item, self.counter)
                self.first_boot_items = True
            # Expand package folder and pass contents to runComponent_
            elif item.get('type') == 'package_folder':
                url = item.get('url').encode("utf8")
                url_path = urlparse.urlparse(urllib2.unquote(url)).path
                if os.path.isdir(url_path):
                    for f in os.listdir(url_path):
                        if os.path.basename(f).endswith('.pkg'):
                            new_url = os.path.join(url, f)
                            item['url'] = new_url
                            item['type'] = 'package'
                            self.runComponent_(item)
                else:
                    raise TypeError("package_folder expected a folder path: %s" %(url))
            # Copy first boot script
            elif item.get('type') == 'script' and item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Copying first boot script %s' % str(self.counter))
                if item.get('url'):
                    if item.get('additional_headers'):
                        (data, error) = Utils.downloadFile(item.get('url'), item.get('additional_headers'))
                        self.copyFirstBootScript(data, self.counter)
                    else:
                        (data, error) = Utils.downloadFile(item.get('url'))
                        self.copyFirstBootScript(data, self.counter)
                else:
                    self.copyFirstBootScript(item.get('content'), self.counter)
                self.first_boot_items = True
            # Run script
            elif item.get('type') == 'script' and not item.get('first_boot', True):
                Utils.sendReport('in_progress', 'Running script %s' % str(self.counter))
                if item.get('url'):
                    if item.get('additional_headers'):
                        (data, error) = Utils.downloadFile(item.get('url'), item.get('additional_headers'))
                        self.runPreFirstBootScript(data, self.counter)
                    else:
                        (data, error) = Utils.downloadFile(item.get('url'))
                        self.runPreFirstBootScript(data, self.counter)
                else:
                    self.runPreFirstBootScript(item.get('content'), self.counter)
            elif item.get('type') == 'script_folder':
                url = item.get('url')
                url_path = urlparse.urlparse(urllib2.unquote(url)).path
                if os.path.isdir(url_path):
                    for f in os.listdir(url_path):
                        new_url = os.path.join(url, f)
                        new_url_path = urlparse.urlparse(urllib2.unquote(new_url)).path
                        if os.path.isfile(new_url_path) and f.startswith(".")==False:
                            item['url'] = new_url
                            item['type'] = 'script'
                            item['first_boot'] = False
                            self.runComponent_(item)
                else:
                    raise TypeError("package_folder expected a folder path: %s" %(url))
            # Partition a disk
            elif item.get('type') == 'partition':
                Utils.sendReport('in_progress', 'Running partition task.')
                self.partitionTargetDisk(item.get('partitions'), item.get('map'))
                if self.future_target == False:
                    # If a partition task is done without a new target specified, no other tasks can be parsed.
                    # Another workflow must be selected.
                    NSLog("No target specified, reverting to workflow selection screen.")

            elif item.get('type') == 'included_workflow':
                Utils.sendReport('in_progress', 'Running included workflow.')
                self.runIncludedWorkflow_(item)

            # Format a volume
            elif item.get('type') == 'eraseVolume':
                if self.targetVolume and not self.targetVolume.filevault:
                    target_volume_string = str(self.targetVolume.mountpoint.encode('utf8')).split('/Volumes/')[-1]
                else: 
                    target_volume_string = 'Macintosh HD'

                Utils.sendReport('in_progress', 'Erasing volume with name %s' % target_volume_string)
                new_volume_name = str(item.get('name', target_volume_string))
                if new_volume_name != target_volume_string:
                    Utils.sendReport('in_progress', 'Volume will be renamed as: %s' % new_volume_name)
                self.eraseTargetVolume(new_volume_name, item.get('format', 'Journaled HFS+'))
            elif item.get('type') == 'computer_name':
                if not item.get('nvram',False):
                    Utils.sendReport('in_progress', 'Setting computer name to %s' % self.computerName)
                    script_dir = os.path.dirname(os.path.realpath(__file__))
                    with open(os.path.join(script_dir, 'set_computer_name.sh')) as script:
                        script=script.read()
                    self.copyFirstBootScript(script, self.counter)
            elif item.get('type') == 'localize':
                Utils.sendReport('in_progress', 'Localizing Mac')
                self.copyLocalize_(item)
                self.first_boot_items = True

            # Workflow specific restart action
            elif item.get('type') == 'restart_action':
                Utils.sendReport('in_progress', 'Setting restart_action to %s' % item.get('action'))
                self.restartAction = item.get('action')
            elif item.get('type') == 'variables':
                self.writeToNVRAM_(self.environmentVariableArray)

            else:
                Utils.sendReport('error', 'Found an unknown workflow item.')
                self.errorMessage = "Found an unknown workflow item."

    def getIncludedWorkflow_(self, item):
        included_workflow = None
        # find the workflow we're looking for
        progress_method = self.updateProgressTitle_Percent_Detail_

        target_workflow = None

        if 'script' in item:
            output_list = []
            if progress_method:
                progress_method("Running script to determine included workflow...", -1, '')
            script = Utils.replacePlaceholders(item.get('script'), self.targetVolume.mountpoint)
            script_file = tempfile.NamedTemporaryFile(delete=False)
            script_file.write(script)
            script_file.close()
            os.chmod(script_file.name, 0700)
            proc = subprocess.Popen(script_file.name, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            while proc.poll() is None:
                output = proc.stdout.readline().strip().decode('UTF-8')
                output_list.append(output)
                if progress_method:
                    progress_method(None, None, output)
            os.remove(script_file.name)
            if proc.returncode != 0:
                error_output = '\n'.join(output_list)
                Utils.sendReport('error', 'Could not run included workflow script: %s' % error_output)
                self.errorMessage = 'Could not run included workflow script: %s' % error_output
                return
            else:

                for line in output_list:
                    if line.startswith("ImagrIncludedWorkflow: ") or line.startswith("ImagrIncludedWorkflow:"):
                        included_workflow = line.replace("ImagrIncludedWorkflow: ", "").replace("ImagrIncludedWorkflow:", "").strip()
                        break
        else:
            included_workflow = item['name']
        NSLog("Log: %@", str(included_workflow))
        if included_workflow == None:
            Utils.sendReport('error', 'No included workflow was returned.')
            self.errorMessage = 'No included workflow was returned.'
            return
        return included_workflow

    def runIncludedWorkflow_(self, item):
        '''Runs an included workflow'''

        included_workflow = self.getIncludedWorkflow_(item)
        if included_workflow:
            for workflow in self.workflows:
                if included_workflow.strip() == workflow['name'].strip():
                    # run the workflow
                    for component in workflow['components']:
                        if (component.get('type') == 'startosinstall' and
                            self.first_boot_items):
                            self.setupFirstBootTools()
                        self.runComponent_(component)
                    return
            else:
                Utils.sendReport('error', 'Could not find included workflow %s' % included_workflow)
                self.errorMessage = 'Could not find included workflow %s' % included_workflow
        else:
            Utils.sendReport('error', 'No included workflow passed %s' % included_workflow)
            self.errorMessage = 'No included workflow passed %s' % included_workflow

    def getVariables(self):
        self.variablePanelLabel.setStringValue_(self.variablesArray[0].values()[0])
        NSApp.beginSheet_modalForWindow_modalDelegate_didEndSelector_contextInfo_(
        self.variablePanel, self.mainWindow, self, None, None)

    def writeToNVRAM_(self,writeArray):

        for currVar in writeArray:

            cmd = ['/usr/sbin/nvram', currVar.keys()[0]+"="+currVar.values()[0] ]
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (eraseOut, eraseErr) = proc.communicate()
            if eraseErr:
                self.errorMessage = eraseErr


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
            elif component.get('computer_name', None):
                self.computerName=Utils.replacePlaceholders(component.get('computer_name'),None)
            else:
                self.computerName = existing_name
            self.theTabView.selectTabViewItem_(self.mainTab)
            if self.variablesArray:
                self.getVariables()
            else:
                self.workflowOnThreadPrep()
        else:
            if component.get('use_serial', False):
                self.computerNameInput.setStringValue_(hardware_info.get('serial_number', ''))
            elif component.get('prefix', None):
                self.computerNameInput.setStringValue_(component.get('prefix'))
            elif component.get('computer_name', None):
                self.computerNameInput.setStringValue_(Utils.replacePlaceholders(component.get('computer_name'),None))
            else:
                self.computerNameInput.setStringValue_(existing_name)

            # Switch to the computer name tab
            self.theTabView.selectTabViewItem_(self.computerNameTab)
            self.mainWindow.makeFirstResponder_(self.computerNameInput)

    @objc.IBAction
    def setComputerName_(self, sender):
        self.computerName = self.computerNameInput.stringValue()
        self.theTabView.selectTabViewItem_(self.mainTab)
        if self.variablesArray:
            self.getVariables()
        else:
            self.workflowOnThreadPrep()

    @objc.python_method
    def Clone(self, source, target, erase=True, verify=True,
              show_activity=True, ramdisk=False):
        """A wrapper around 'asr' to clone one disk object onto another.

        We run with --puppetstrings so that we get non-buffered output that we
        can actually read when show_activity=True.

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

        if ramdisk:
            ramdisksource = self.RAMDisk(source, imaging=True)
            if ramdisksource[0]:
                source = ramdisksource[0]
            else:
                if ramdisksource[1] is True:
                    pass
                else:
                    self.errorMessage = ramdisksource[2]
                    self.targetVolume.EnsureMountedWithRefresh()
                    return False

        is_apfs = False
        if Utils.is_apfs(source):
            is_apfs = True
            # we need to restore to a whole disk here
            if not self.targetVolume.wholedisk:
                target_ref = "/dev/%s" % self.targetVolume._attributes['ParentWholeDisk']
        command = ["/usr/sbin/asr", "restore", "--source", str(source),
                   "--target", target_ref, "--noprompt", "--puppetstrings"]

        self.targetVolume.EnsureMountedWithRefresh()
        if 'FilesystemType' not in self.targetVolume._attributes:
            NSLog("Key `FilesystemType` not found in target volume: %@", str(self.targetVolume._attributes))
            raise TypeError(self.targetVolume._attributes)
        
        if self.targetVolume._attributes['FilesystemType'] == 'hfs' and\
        is_apfs == True:
            self.errorMessage = "%s is formatted as HFS and you are trying to restore an APFS disk image" % str(self.targetVolume.mountpoint)
            self.targetVolume.EnsureMountedWithRefresh()
            return False
        elif self.targetVolume._attributes['FilesystemType'] == 'apfs' and\
        is_apfs == False:
            self.errorMessage = "%s is formatted as APFS and you are trying to restore an HFS disk image" % str(self.targetVolume.mountpoint)
            self.targetVolume.EnsureMountedWithRefresh()
            return False

        if erase:
            # check we can unmount the target... may as well fail here than later.
            if self.targetVolume.Mounted():
                self.targetVolume.Unmount()
            command.append("--erase")

        if not verify:
            command.append("--noverify")

        count=0
        output_string=""
        for x in command:
            output_string = output_string + '\"%s\" '%x

        NSLog(u"%@",output_string)

        self.updateProgressTitle_Percent_Detail_('Restoring %s' % source, -1, '')
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
            self.targetVolume.EnsureMountedWithRefresh()
            if 'ramdisk' in source:
                NSLog(u"Detaching RAM Disk post imaging.")
                detachcommand = ["/usr/bin/hdiutil", "detach",
                                 ramdisksource[1]]
                detach = subprocess.Popen(detachcommand,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
            return True

    @objc.python_method
    def startOSinstall(self, item, ramdisk):
        if ramdisk:
            ramdisksource = self.RAMDisk(item, imaging=False)
            if ramdisksource[0]:
                ositem = {
                    'ramdisk': True,
                    'type': 'startosinstall',
                    'url': ramdisksource[0]
                    }
            else:
                if ramdisksource[1] is True:
                    ositem = item
                else:
                    self.errorMessage = ramdisksource[2]
                    self.targetVolume.EnsureMountedWithRefresh()
                    return False
        else:
            ositem = item
        self.updateProgressTitle_Percent_Detail_(
            'Preparing macOS install...', -1, '')
        success, detail = osinstall.run(
            ositem, self.targetVolume.mountpoint,
            progress_method=self.updateProgressTitle_Percent_Detail_)
        if not success:
            self.errorMessage = detail

    @objc.python_method
    def RAMDisk(self, source, imaging=False):
        if imaging is True:
            apfs_image = Utils.is_apfs(source)
            
            if 'FilesystemType' not in self.targetVolume._attributes:
                NSLog("Key `FilesystemType` not found in target volume: %@", str(self.targetVolume._attributes))
                raise TypeError(self.targetVolume._attributes)
                    
            if self.targetVolume._attributes['FilesystemType'] == 'hfs' and apfs_image is True:
                error = "%s is formatted as HFS and you are trying to restore an APFS disk image" % str(self.targetVolume.mountpoint)
                return False, False, error
            elif self.targetVolume._attributes['FilesystemType'] == 'apfs' and apfs_image is False:
                error = "%s is formatted as APFS and you are trying to restore an HFS disk image" % str(self.targetVolume.mountpoint)
                return False, False, error
        sysctlcommand = ["/usr/sbin/sysctl", "hw.memsize"]
        sysctl = subprocess.Popen(sysctlcommand,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        memsizetuple = sysctl.communicate()
        # sysctl returns crappy things from stdout.
        # Ex: ('hw.memsize: 1111111\n', '')
        memsize = int(
            memsizetuple[0].split('\n')[0].replace('hw.memsize: ', ''))
#        NSLog(u"Total Memory is %@", str(memsize))
        # Assume netinstall uses at least 650MB of RAM. If we don't require
        # enough RAM, gurl will timeout or cause RecoveryOS to crash.
        availablemem = memsize - 681574400
#        NSLog(u"Available Memory for DMG is %@", str(availablemem))
        if imaging is True:
            filesize = Utils.getDMGSize(source)[0]
        else:
            filesize = Utils.getDMGSize(source.get('url'))[0]
#        NSLog(u"Required Memory for DMG is %@", str(filesize))
        # Formatting RAM Disk requires around 5% of the total amount of
        # bytes. Add 10% to compensate for the padding we will need.
        paddedfilesize = int(filesize) * 1.10
#        NSLog(u"Padded Memory for DMG is %@", str(paddedfilesize))
        if filesize is False:
#            NSLog(u"Error when calculating source size. Using original method "
#                  "instead of gurl...")
            return False, True
        elif imaging is True and 9000000000 > memsize:
            NSLog(u"Feature requires more than 9GB of RAM. Using asr "
                  "instead of gurl...")
            return False, True
        elif int(paddedfilesize) > availablemem:
            NSLog(u"Available Memory is not sufficient for source size. "
                  "Using original method instead of gurl...")
            return False, True
        elif 8000000000 > memsize:
            NSLog(u"Feature requires at least 8GB of RAM. Using original "
                  "method instead of gurl...")
            return False, True
        else:
            sectors = int(paddedfilesize) / 512
            ramstring = "ram://%s" % str(sectors)
            NSLog(u"Amount of Sectors for RAM Disk is %@", str(sectors))
            ramattachcommand = ["/usr/bin/hdiutil", "attach", "-nomount",
                                ramstring]
            ramattach = subprocess.Popen(ramattachcommand,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
            devdisk = ramattach.communicate()
            # hdiutil returns some really crappy things from stdout
            # Ex: ('/dev/disk20     \t         \t\n', '')
            devdiskstr = devdisk[0].split(' ')[0]
            randomnum = random.randint(1000000, 10000000)
            ramdiskvolname = "ramdisk" + str(randomnum)
            NSLog(u"RAM Disk mountpoint is %@", str(ramdiskvolname))
            NSLog(u"Formatting RAM Disk as HFS at %@", devdiskstr)
            ramformatcommand = ["/sbin/newfs_hfs", "-v",
                                ramdiskvolname, devdiskstr]
            ramformat = subprocess.Popen(ramformatcommand,
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE)
            NSLog(u"Mounting HFS RAM Disk %@", devdiskstr)
            rammountcommand = ["/usr/sbin/diskutil", "erasedisk",
                               'HFS+', ramdiskvolname, devdiskstr]
            rammount = subprocess.Popen(rammountcommand,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
            # Wait for the disk to completely initialize
            targetpath = os.path.join('/Volumes', ramdiskvolname)
            while not os.path.isdir(targetpath):
                NSLog(u"Sleeping 1 second to allow full disk initialization.")
                time.sleep(1)
            if imaging is True:
                dmgsource = source
            else:
                dmgsource = source.get('url')
            NSLog(u"Downloading DMG file from %@", str(dmgsource))
            download_string = 'Downloading {}...'.format(str(dmgsource))
            self.updateProgressTitle_Percent_Detail_(
            download_string, -1, '')
            sourceram = self.downloadDMG(dmgsource, targetpath)
            if sourceram is False:
                NSLog(u"Detaching RAM Disk due to failure.")
                detachcommand = ["/usr/bin/hdiutil", "detach", devdiskstr]
                detach = subprocess.Popen(detachcommand,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE)
                error = "DMG Failed to download via RAMDisk."
                return False, False, error
            return sourceram, devdiskstr

    def downloadAndInstallPackages_(self, item):
        url = item.get('url')
        custom_headers = item.get('additional_headers')
        self.updateProgressTitle_Percent_Detail_('Installing packages...', -1, '')
        # mount the target
        self.targetVolume.EnsureMountedWithRefresh()

        package_name = os.path.basename(url)
        self.downloadAndInstallPackage(
            url, self.targetVolume.mountpoint,
            progress_method=self.updateProgressTitle_Percent_Detail_,
            additional_headers=custom_headers)

    @objc.python_method
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
                return False, self.errorMessage

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
                return False, self.errorMessage

        if os.path.basename(url).endswith('.pkg'):

            # Make our temp directory on the target
            temp_dir = tempfile.mkdtemp(dir=target)
            # Download it
            packagename = os.path.basename(url)
            if url.startswith("file://"):
                url_parse = urlparse.urlparse(url)
                downloaded_file=url_parse.path.replace("%20", " ")
            else:
                (downloaded_file, error) = Utils.downloadChunks(url, os.path.join(temp_dir,
                packagename), additional_headers=additional_headers)
                if error:
                    self.errorMessage = "Couldn't download - %s \n %s" % (url, error)
                    return False
            # Install it
            retcode = self.installPkg(downloaded_file, target, progress_method=progress_method)
            if retcode != 0:
                self.errorMessage = "Couldn't install %s" % downloaded_file
                return False
            # Clean up after ourselves
            shutil.rmtree(temp_dir)

    @objc.python_method
    def downloadDMG(self, url, target):
        if os.path.basename(url).endswith('.dmg'):
            # Download it
            dmgname = os.path.basename(url)
            failsleft = 3
            dmgpath = os.path.join(target, dmgname)
            while not os.path.isfile(dmgpath):
                (dmg, error) = Utils.downloadChunks(url, dmgpath, resume=True,
                                                    progress_method=self.updateProgressTitle_Percent_Detail_)
                if error:
                    failsleft -= 1
                    NSLog(u"DMG failed to download - Retries left: %@", str(failsleft))
                if failsleft == 0:
                    NSLog(u"Too many download failures. Exiting...")
                    break
            if failsleft == 0:
                return False
        else:
            self.errorMessage = "%s doesn't end with '.dmg'" % url
            return False
        return dmg

    @objc.python_method
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

    @objc.python_method
    def downloadPackage(self, url, target, number, progress_method=None, additional_headers=None):
        error = None
        dest_dir = os.path.join(target, 'private/var/.imagr/first-boot/items')
        if not os.path.exists(dest_dir):
            self.setupFirstBootDir()
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

    @objc.python_method
    def copyPkgFromDmg(self, url, dest_dir, number):
        error = None
        # We're going to mount the dmg
        try:
            dmgmountpoints = Utils.mountdmg(url)
            dmgmountpoint = dmgmountpoints[0]
        except:
            self.errorMessage = "Couldn't mount %s" % url
            return False, self.errorMessage

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

    @objc.python_method
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

    @objc.python_method
    def runPreFirstBootScript(self, script, counter):
        self.updateProgressTitle_Percent_Detail_(
            'Preparing to run scripts...', -1, '')
        # mount the target
        if not self.targetVolume.Mounted():
            self.targetVolume.Mount()


        # if the script wipes out the partition, we keep a record of the parent disk.
        if not self.targetVolume.Info()['WholeDisk'] and 'IORegistryEntryName' in self.targetVolume._attributes:
            parent_disk = macdisk.Disk(self.targetVolume.Info()['ParentWholeDisk'])
            is_apfs_target = parent_disk._attributes['IORegistryEntryName'] == "AppleAPFSMedia"
        else:
            is_apfs_target = False
            NSLog("Not a child of APFS")

        if 'IORegistryEntryName' in self.targetVolume._attributes:
            is_efi_target = self.targetVolume._attributes['IORegistryEntryName'] == "EFI System Partition"

        retcode, error_output = self.runScript(
            script, self.targetVolume.mountpoint,
            progress_method=self.updateProgressTitle_Percent_Detail_)

        if retcode != 0:
            if error_output is not None:
                self.errorMessage = error_output
            else:
                self.errorMessage = "Script %s returned a non-0 exit code" % str(int(counter))
        else:
            
            try:
                is_apfs_target
            except NameError:
                is_apfs_target = False

            if is_apfs_target:
                # If it was formatted back to HFS+ as part of a script execution, then we have to scan all available
                # devices to discover the physical container.

                # It is possible that a script has modified the partition/volume name.
                # If the user initially selected a partition on an APFS container disk, the physical disk won't have the
                # same name, nor will it be the parent disk of the container, so we need to refresh all disks.
                # eg. apfs deleteContainer (disk1s1)
                # -> now we have a partition on disk0s1 because APFS container disk1 disappeared.
                # To solve this problem, any time you run deleteContainer from a script, the volume name should be "Imagr_APFS_Deleted"
                self.should_update_volume_list = True

                volumes = macdisk.MountedVolumes()
                for volume in volumes:
                    if volume.Info()['VolumeName'] == "Imagr_APFS_Deleted":
                        self.targetVolume = volume
                        break


    @objc.python_method
    def runScript(self, script, target, progress_method=None):
        """
        Replaces placeholders in a script and then runs it.
        """
        # replace the placeholders in the script
        script = Utils.replacePlaceholders(script, target)
        if self.computerName:
            script = Utils.replacePlaceholders(script, target,self.computerName)

        error_output = None
        output_list = []
        # Copy script content to a temporary location and make executable
        script_file = tempfile.NamedTemporaryFile(delete=False)
        script_file.write(script)
        script_file.close()
        os.chmod(script_file.name, 0700)
        if progress_method:
            progress_method("Running script...", -1, '')
        my_env = os.environ.copy()
        url_parse = urlparse.urlparse(Utils.getServerURL())
        my_env["server_path"]=url_parse.path
        proc = subprocess.Popen(script_file.name, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True,env=my_env)
        while proc.poll() is None:
            output = proc.stdout.readline().strip().decode('UTF-8')
            output_list.append(output)
            if progress_method:
                progress_method(None, None, output)
        os.remove(script_file.name)
        if proc.returncode != 0:
            error_output = '\n'.join(output_list)
        return proc.returncode, error_output

    @objc.python_method
    def copyScript(self, script, target, number, progress_method=None):
        """
        Copies a
         script to a specific volume
        """
        dest_dir = os.path.join(target, 'private/var.imagr/first-boot/items')
        if not os.path.exists(dest_dir):
            self.setupFirstBootDir()
        dest_file = os.path.join(dest_dir, "%03d" % number)
        if progress_method:
            progress_method("Copying script to %s" % dest_file, 0, '')
        # convert placeholders
        if self.computerName or self.keyboard_layout_id or self.keyboard_layout_name or self.language or self.locale or self.timezone:
            script = Utils.replacePlaceholders(script, target, self.computerName, self.keyboard_layout_id, self.keyboard_layout_name, self.language, self.locale, self.timezone)
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
            self.reloadVolumes()
            self.enableWorkflowViewControls()
            self.chooseImagingTarget_(None)
            # self.loadDataComplete()

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

    @objc.python_method
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
                        NSLog("%@",phase)
                        if progress_method:
                            progress_method(None, None, phase)
                elif msg.startswith("STATUS:"):
                    status = msg[7:]
                    if status:
                        NSLog("%@",status)
                        if progress_method:
                            progress_method(None, None, status)
                elif msg.startswith("%"):
                    percent = float(msg[1:])
                    NSLog("%@ percent complete", percent)
                    if progress_method:
                        progress_method(None, percent, None)
                elif msg.startswith(" Error"):
                    NSLog("%@",msg)
                    if progress_method:
                        progress_method(None, None, msg)
                elif msg.startswith(" Cannot install"):
                    NSLog("%@",msg)
                    if progress_method:
                        progress_method(None, None, msg)
                else:
                    NSLog("%@",msg)
                    if progress_method:
                        progress_method(None, None, msg)

        return proc.returncode

    @objc.python_method
    def partitionTargetDisk(self, partitions=None, partition_map="GPTFormat", progress_method=None):
        """
        Formats a target disk according to specifications.
        'partitions' is a list of dictionaries of partition mappings for names, sizes, formats.
        'partition_map' is a volume map type - MBR, GPT, or APM.
        """
        # self.targetVolume.mountpoint should be the actual volume we're targeting.
        # self.targetVolume is the macdisk object that can be queried for its parent disk
        parent_disk = self.targetVolume.Info()['ParentWholeDisk']

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
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (partOut, partErr) = proc.communicate()
        if partErr:
            NSLog("Error occurred: %@", partErr)
            self.errorMessage = partErr
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

    @objc.python_method
    def eraseTargetVolume(self, name='Macintosh HD', format='Journaled HFS+', progress_method=None):
        """
        Erases the target volume.
        'name' can be used to rename the volume on reformat.
        'format' can be used to specify a format type.
        'format' type of 'auto_hfs_or_apfs' will check for HFS+ or APFS
        If no options are provided, it will format the volume with name 'Macintosh HD' with JHFS+.
        """

        if format == 'auto_hfs_or_apfs':
            if self.targetVolume._attributes['FilesystemType'] == 'hfs':
                format='Journaled HFS+'
                NSLog("Detected HFS+ - erasing target")
                cmd = ['/usr/sbin/diskutil', 'eraseVolume', format, name, self.targetVolume.mountpoint ]

                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (eraseOut, eraseErr) = proc.communicate()
                if eraseErr:
                    NSLog("Error occurred when erasing volume: %@", eraseErr)
                    self.errorMessage = eraseErr
                if self.targetVolume.filevault:
                    self.targetVolume.filevault=False

            elif self.targetVolume._attributes['FilesystemType'] == 'apfs':
                format='APFS'
                parent_disk = self.targetVolume.Info()['ParentWholeDisk']

                if self.targetVolume.filevault==False:
                    NSLog("Detected non-filevaulted APFS - unmount and mounting all partitions to make sure nothing is holding on to them prior to erasing")

                    if not macdisk.Disk(parent_disk).Unmount():
                        self.errorMessage = "Error unmounting volumes on target prior to erase. Restart and try again."
                        macdisk.Disk(parent_disk).Mount()
                        return
                    if not macdisk.Disk(parent_disk).Mount():
                        self.errorMessage = "Error Mounting all volumes on disk. Restart and try again."
                        return


                NSLog("Removing APFS volumes")
                self.targetVolume=Utils.reset_apfs_container(self.targetVolume.deviceidentifier,name)
                if (self.targetVolume==None):
                    self.errorMessage = "The new APFS volume could not be found"
                    return
            else:
                NSLog("Volume not HFS+ or APFS, system returned: %@", self.targetVolume._attributes['FilesystemType'])
                self.errorMessage = "Not HFS+ or APFS - specify volume format and reload workflows."
                return

        # Reload possible targets because original target name might not exist
        self.should_update_volume_list = True
        self.targetVolume.EnsureMountedWithRefresh()

    def copyLocalize_(self, item):
        if 'keyboard_layout_name' in item:
            self.keyboard_layout_name = item['keyboard_layout_name']

        if 'keyboard_layout_id' in item:
            self.keyboard_layout_id = item['keyboard_layout_id']

        if 'language' in item:
            self.language = item['language']

        if 'locale' in item:
            self.locale = item['locale']

        if 'timezone' in item:
            self.timezone = item['timezone']

        script_dir = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(script_dir, 'localize.sh')) as script:
            script=script.read()
        self.copyFirstBootScript(script, self.counter)

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

    
