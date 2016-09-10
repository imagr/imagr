"""Default settings."""
import os
# pylint: disable=line-too-long

# main module
MACHINEINFO = '/Library/Preferences/com.megacorp.machineinfo.plist'
IMAGEINFO = '/Library/Preferences/com.megacorp.imageinfo.plist'

# airport module
GUEST_NETWORKS = ['MegacorpGuest', 'MegacorpGuestPSK']
GUEST_PSKS = ['hunter2', 'publicpassword']

# cocoadialog module
COCOADIALOG_PATH = os.path.dirname(os.path.realpath(__file__))+'/CocoaDialog.app'

# experiments module
EXPERIMENTS_YAML = '/var/db/puppet/experiments.yaml'

# profiles module
NETWORK_PROFILE_ID = 'com.megacorp.networkprofile'
ORGANIZATION_NAME = 'Megacorp Inc.'

# systemconfig module
CORP_PROXY = 'https://proxyconfig.megacorp.com/proxy.pac'

# wifi_network_order module
SSIDS = ['MegaWifi$WPA2E']
