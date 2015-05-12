#!/bin/bash

NAME="{{computer_name}}"

/usr/sbin/scutil --set ComputerName "$NAME"
/usr/sbin/scutil --set HostName "$NAME"
/usr/sbin/scutil --set LocalHostName "$NAME"
