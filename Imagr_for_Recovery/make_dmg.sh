#!/bin/sh

# Builds a disk image containing Imagr and config.

THISDIR=$(/usr/bin/dirname ${0})
DMGNAME="${THISDIR}/imagr.dmg"
if [[ -e "${DMGNAME}" ]] ; then
    /bin/rm "${DMGNAME}"
fi
/usr/bin/hdiutil create -fs HFS+ -srcfolder "${THISDIR}/imagr" "${DMGNAME}"