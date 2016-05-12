#!/bin/bash

PLBUDDY=/usr/libexec/PlistBuddy
NAME="{{keyboard_layout_name}}"
LAYOUT="{{keyboard_layout_id}}"
LANG="{{language}}"
LOCALE="{{locale}}"
TIMEZONE="{{timezone}}"
update_kdb_layout() {
    ${PLBUDDY} -c "Delete :AppleCurrentKeyboardLayoutInputSourceID" "${1}" &>/dev/null
    echo "Setting current keyboard layout to com.apple.keylayout.${NAME}"
    ${PLBUDDY} -c "Add :AppleCurrentKeyboardLayoutInputSourceID string com.apple.keylayout.${NAME}" "${1}"
    echo "Setting keyboard layout name to ${NAME}"
    echo "Setting keyboard layout ID to ${LAYOUT}"
    for SOURCE in AppleDefaultAsciiInputSource AppleCurrentAsciiInputSource AppleCurrentInputSource AppleEnabledInputSources AppleSelectedInputSources AppleInputSourceHistory
    do
        ${PLBUDDY} -c "Delete :${SOURCE}" "${1}" &>/dev/null
        ${PLBUDDY} -c "Add :${SOURCE} array" "${1}"
        ${PLBUDDY} -c "Add :${SOURCE}:0 dict" "${1}"
        ${PLBUDDY} -c "Add :${SOURCE}:0:InputSourceKind string 'Keyboard Layout'" "${1}"
        ${PLBUDDY} -c "Add ':${SOURCE}:0:KeyboardLayout ID' integer ${LAYOUT}" "${1}"
        ${PLBUDDY} -c "Add ':${SOURCE}:0:KeyboardLayout Name' string '${NAME}'" "${1}"
    done
}

update_language() {
    ${PLBUDDY} -c "Delete :AppleLanguages" "${1}" &>/dev/null
    echo "Setting Language to ${LANG}"
    ${PLBUDDY} -c "Add :AppleLanguages array" "${1}"
    ${PLBUDDY} -c "Add :AppleLanguages:0 string '${LANG}'" "${1}"
}

update_locale() {
    echo "Setting Locale to ${LOCALE}"
    ${PLBUDDY} -c "Delete :AppleLocale" "${1}" &>/dev/null
    ${PLBUDDY} -c "Add :AppleLocale string ${LOCALE}" "${1}" &>/dev/null
    echo "Setting Country to ${LOCALE:3:2}"
    ${PLBUDDY} -c "Delete :Country" "${1}" &>/dev/null
    ${PLBUDDY} -c "Add :Country string ${LOCALE:3:2}" "${1}" &>/dev/null
}

if [ -n "$NAME" ] || [ -n "$LAYOUT" ]; then
  update_kdb_layout "/Library/Preferences/com.apple.HIToolbox.plist" "${NAME}" "${LAYOUT}"
fi

if [ -n "$LANG" ]; then
    update_language "/Library/Preferences/.GlobalPreferences.plist" "${LANG}"
fi

if [ -n "$LOCALE" ]; then
    update_locale "/Library/Preferences/.GlobalPreferences.plist" "${LOCALE}"
fi

if [ -n "$TIMEZONE" ]; then
    /usr/sbin/systemsetup -settimezone ${TIMEZONE}
fi
