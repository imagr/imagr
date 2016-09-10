//
//  LLBorderlessWindow.h
//  Imagr
//
//  Created by Per Olofsson on 2016-05-13.
//  Copyright © 2016 Graham Gilbert. All rights reserved.
//

#import <Cocoa/Cocoa.h>

@interface LLBorderlessWindow : NSWindow

- (id) initWithContentRect:(NSRect)contentRect
                 styleMask:(unsigned int)aStyle
                   backing:(NSBackingStoreType)bufferingType
                     defer:(BOOL)flag;

@end
