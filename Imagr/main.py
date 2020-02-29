# -*- coding: utf-8 -*-
#
#  main.py
#  Imagr
#
#  Created by Graham Gilbert on 04/04/2015.
#  Copyright (c) 2015 Graham Gilbert. All rights reserved.
#

# import modules required by application
import objc
import Foundation
import AppKit

from PyObjCTools import AppHelper

# import modules containing classes required to start application and load MainMenu.nib
import AppDelegate
import MainController
import LLLogWindowController

# pass control to AppKit
AppHelper.runEventLoop()
