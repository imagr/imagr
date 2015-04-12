#-*- coding: utf-8 -*-
#
#  LLLogWindowController.py
#  LoginLog
#
#  Created by Pelle on 2013-03-05.
#  Copyright (c) 2013 Göteborgs universitet. All rights reserved.
#

from objc import YES, NO, IBAction, IBOutlet
from Foundation import *
from AppKit import *


class LLLogViewDataSource(NSObject):
    
    """Data source for an NSTableView that displays an array of text lines.\n"""
    """Line breaks are assumed to be LF, and partial lines from incremental """
    """reading is handled."""
    
    logFileData = NSMutableArray.alloc().init()
    lastLineIsPartial = False
    
    def addLine_partial_(self, line, isPartial):
        if self.lastLineIsPartial:
            joinedLine = self.logFileData.lastObject() + line
            self.logFileData.removeLastObject()
            self.logFileData.addObject_(joinedLine)
        else:
            self.logFileData.addObject_(line)
        self.lastLineIsPartial = isPartial
    
    def removeAllLines(self):
        self.logFileData.removeAllObjects()
    
    def lineCount(self):
        return self.logFileData.count()
    
    def numberOfRowsInTableView_(self, tableView):
        return self.lineCount()
    
    def tableView_objectValueForTableColumn_row_(self, tableView, column, row):
        return self.logFileData.objectAtIndex_(row)
    

class LLLogWindowController(NSObject):
    
    window = IBOutlet()
    logView = IBOutlet()
    backdropWindow = IBOutlet()
    logFileData = LLLogViewDataSource.alloc().init()
    fileHandle = None
    updateTimer = None
    
    def showLogWindow_(self, title):
        # Base all sizes on the screen's dimensions.
        screenRect = NSScreen.mainScreen().frame()
        
        # Open a log window that covers most of the screen.
        self.window.setTitle_(title)
        self.window.setCanBecomeVisibleWithoutLogin_(True)
        self.window.setLevel_(NSScreenSaverWindowLevel - 1)
        self.window.orderFrontRegardless()
        # Resize the log window so that it leaves a border on all sides.
        # Add a little extra border at the bottom so we don't cover the
        # loginwindow message.
        windowRect = screenRect.copy()
        windowRect.origin.x = 100.0
        windowRect.origin.y = 200.0
        windowRect.size.width -= 200.0
        windowRect.size.height -= 300.0
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(0.5)
        self.window.animator().setFrame_display_(windowRect, True)
        NSAnimationContext.endGrouping()
        
        # Create a transparent, black backdrop window that covers the whole
        # screen and fade it in slowly.
        self.backdropWindow.setCanBecomeVisibleWithoutLogin_(True)
        self.backdropWindow.setLevel_(NSStatusWindowLevel)
        self.backdropWindow.setFrame_display_(screenRect, True)
        translucentColor = NSColor.blackColor().colorWithAlphaComponent_(0.75)
        self.backdropWindow.setBackgroundColor_(translucentColor)
        self.backdropWindow.setOpaque_(False)
        self.backdropWindow.setIgnoresMouseEvents_(False)
        self.backdropWindow.setAlphaValue_(0.0)
        self.backdropWindow.orderFrontRegardless()
        NSAnimationContext.beginGrouping()
        NSAnimationContext.currentContext().setDuration_(2.0)
        self.backdropWindow.animator().setAlphaValue_(1.0)
        NSAnimationContext.endGrouping()
    
    def watchLogFile_(self, logFile):
        # Display and continuously update a log file in the main window.
        self.stopWatching()
        self.logFileData.removeAllLines()
        self.logView.setDataSource_(self.logFileData)
        self.logView.reloadData()
        self.fileHandle = NSFileHandle.fileHandleForReadingAtPath_(logFile)
        self.refreshLog()
        # Kick off a timer that updates the log view periodically.
        self.updateTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.25,
            self,
            u"refreshLog",
            None,
            YES
        )
    
    def stopWatching(self):
        # Release the file handle and stop the update timer.
        if self.fileHandle is not None:
            self.fileHandle.closeFile()
            self.fileHandle = None
        if self.updateTimer is not None:
            self.updateTimer.invalidate()
            self.updateTimer = None
    
    def refreshLog(self):
        # Check for new available data, read it, and scroll to the bottom.
        data = self.fileHandle.availableData()
        if data.length():
            utf8string = NSString.alloc().initWithData_encoding_(
                data,
                NSUTF8StringEncoding
            )
            for line in utf8string.splitlines(True):
                if line.endswith(u"\n"):
                    self.logFileData.addLine_partial_(line.rstrip(u"\n"), False)
                else:
                    self.logFileData.addLine_partial_(line, True)
            self.logView.reloadData()
            self.logView.scrollRowToVisible_(self.logFileData.lineCount() - 1)
    
