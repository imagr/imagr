#-*- coding: utf-8 -*-
#
#  main.py
#  LoginLog
#
#  Created by Pelle on 2013-03-05.
#  Copyright Göteborgs universitet 2013. All rights reserved.
#

#import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import LLAppDelegate
import LLLogWindowController

# pass control to AppKit
AppHelper.runEventLoop()
