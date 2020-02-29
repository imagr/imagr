# -*- coding: utf-8 -*-
#
#  AppDelegate.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

from Foundation import *
from AppKit import *
import Utils
import macdisk
import shutil
class AppDelegate(NSObject):
    
    mainController = objc.IBOutlet()

    logWindowController = objc.IBOutlet()
    prefs = NSUserDefaults.standardUserDefaults()

    @objc.IBAction
    def saveLog_(self,sender):
        savepanel=NSSavePanel.savePanel()
        savepanel.setMessage_(u'Specify a name and location to save log:')
        savepanel.setAllowedFileTypes_(["log"])
        res=savepanel.runModal()
        if res != NSModalResponseOK:
            return

        save_path=savepanel.URL().path()
        shutil.copy(u'/var/log/install.log', save_path)
        
    @objc.IBAction
    def showLogWindow_(self,sender):
        logfile = self.prefs.stringForKey_(u"logfile")
        style = self.prefs.stringForKey_(u"style")
        self.logWindowController.showLogWindow_withStyle_(logfile,'normal')
        self.logWindowController.watchLogFile_(logfile)

    def applicationDidFinishLaunching_(self, sender):
        self.prefs.registerDefaults_({
            u"logfile": u"/var/log/install.log",
            u"style": u"focused",

        })

        self.showLogWindow_(self)


        dict = NSBundle.mainBundle().infoDictionary()

        Utils.bringToFront(dict["CFBundleIdentifier"]);
        if self.mainController:
            self.mainController.runStartupTasks()
        if NSApp.respondsToSelector_('disableRelaunchOnLogin'):
            NSApp.disableRelaunchOnLogin()

    def applicationWillTerminate_(self, notification):
        # be nice and remove our observers from NSWorkspace
        nc = NSWorkspace.sharedWorkspace().notificationCenter()
        nc.removeObserver_(self.mainController)
