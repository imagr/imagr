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
class AppDelegate(NSObject):
    
    mainController = objc.IBOutlet()
    
    def applicationDidFinishLaunching_(self, sender):

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
