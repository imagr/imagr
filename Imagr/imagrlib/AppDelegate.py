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

class AppDelegate(NSObject):
    
    mainController = objc.IBOutlet()
    
    def applicationDidFinishLaunching_(self, sender):
        NSLog("Application did finish launching.")
        if self.mainController:
            self.mainController.runStartupTasks()
        
        if NSApp.respondsToSelector_('disableRelaunchOnLogin'):
            NSApp.disableRelaunchOnLogin()
