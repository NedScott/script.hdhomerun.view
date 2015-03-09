# -*- coding: utf-8 -*-
import sys, binascii, json
import xbmc, xbmcaddon

DEBUG = True

ADDON = xbmcaddon.Addon()

def LOG(msg):
    print 'script.hdhomerun.view: {0}'.format(msg)

def DEBUG_LOG(msg):
    if not DEBUG: return
    LOG(msg)

def ERROR(txt='',hide_tb=False,notify=False):
    if isinstance (txt,str): txt = txt.decode("utf-8")
    short = str(sys.exc_info()[1])
    if hide_tb:
        LOG('ERROR: {0} - {1}'.format(txt,short))
        return short
    print "_________________________________________________________________________________"
    LOG('ERROR: ' + txt)
    import traceback
    tb = traceback.format_exc()
    for l in tb.splitlines(): print '    ' + l
    print "_________________________________________________________________________________"
    print "`"
    if notify: showNotification('ERROR: {0}'.format(short))
    return short

def getSetting(key,default=None):
    setting = ADDON.getSetting(key)
    return _processSetting(setting,default)

def _processSetting(setting,default):
    if not setting: return default
    if isinstance(default,bool):
        return setting.lower() == 'true'
    elif isinstance(default,float):
        return float(setting)
    elif isinstance(default,int):
        return int(float(setting or 0))
    elif isinstance(default,list):
        if setting: return json.loads(binascii.unhexlify(setting))
        else: return default

    return setting

def setSetting(key,value):
    value = _processSettingForWrite(value)
    ADDON.setSetting(key,value)

def _processSettingForWrite(value):
    if isinstance(value,list):
        value = binascii.hexlify(json.dumps(value))
    elif isinstance(value,bool):
        value = value and 'true' or 'false'
    return str(value)

def showNotification(message,time_ms=3000,icon_path=None,header='XBMC TTS'):
    try:
        icon_path = icon_path or xbmc.translatePath(ADDON.getAddonInfo('icon')).decode('utf-8')
        xbmc.executebuiltin('Notification({0},{1},{2},{3})'.format(header,message,time_ms,icon_path))
    except RuntimeError: #Happens when disabling the addon
        LOG(message)

def videoIsPlaying():
    return xbmc.getCondVisibility('Player.HasVideo')