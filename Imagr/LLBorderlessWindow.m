//
//  LLBorderlessWindow.m
//  Imagr
//
//  Created by Per Olofsson on 2016-05-13.
//  Copyright © 2016 Graham Gilbert. All rights reserved.
//

#import "LLBorderlessWindow.h"

@implementation LLBorderlessWindow

- (id) initWithContentRect:(NSRect)contentRect
                 styleMask:(unsigned int)aStyle
                   backing:(NSBackingStoreType)bufferingType
                     defer:(BOOL)flag
{
    self = [super initWithContentRect:contentRect
                            styleMask:NSBorderlessWindowMask
                              backing:bufferingType
                                defer:flag];
    return self;
}

@end
