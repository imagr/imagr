#-*- coding: utf-8 -*-
#
#  LoginLogAppDelegate.py
#  LoginLog
#
#  Created by Pelle on 2013-03-05.
#  Copyright Göteborgs universitet 2013. All rights reserved.
#

from objc import IBOutlet
from Foundation import *
from AppKit import *


class LLAppDelegate(NSObject):
    
    logWindowController = IBOutlet()
    prefs = NSUserDefaults.standardUserDefaults()
    
    def applicationDidFinishLaunching_(self, sender):
        self.prefs.registerDefaults_({
            u"logfile": u"/var/log/system.log",
        })
        logfile = self.prefs.stringForKey_(u"logfile")
        self.logWindowController.showLogWindow_(logfile)
        self.logWindowController.watchLogFile_(logfile)
    
