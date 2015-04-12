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
import MainController
class AppDelegate(NSObject):
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
    def applicationDidFinishLaunching_(self, sender):
        NSLog("Application did finish launching.")
        if self.mainWindow:
            #self.mainWindow.setCanBecomeVisibleWithoutLogin_(True)
            #self.mainWindow.setLevel_(NSScreenSaverWindowLevel - 1)
            self.mainWindow.center()

        if NSApp.respondsToSelector_('disableRelaunchOnLogin'):
            NSApp.disableRelaunchOnLogin()
