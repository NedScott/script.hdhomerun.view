# -*- coding: utf-8 -*-
import os
import xbmc, xbmcvfs
import util

#Skins that work without font modification:
#
# skin.aeon.nox.5
# skin.xperience1080

FONT_TRANSLATIONS = {
    'skin.arctic.zephyr':{'font10':'Mini',                  'font13':'font13',       'font30':'Large'},
    'skin.apptv':       {'font10':'font10',                 'font13':'font10',      'font30':'font18'}, #No font10 equivalent
    'skin.eminence':    {'font10':'Font-RSS',               'font13':'font13',      'font30':'Font-ViewCategory'},
    'skin.amber':       {'font10':'GridItems',              'font13':'Details',     'font30':'MainLabelBigTitle'}, #Old gui API level - alignment flaws
    'skin.metropolis':  {'font10':'METF_DialogVerySmall',   'font13':'font13',      'font30':'METF_TitleTextLarge'},
    'skin.quartz':      {'font10':'size14',                 'font13':'font13',      'font30':'size28'} #Old gui API level - alignment flaws
}

#helix skins to check =  [' skin.mimic', ' skin.neon', ' skin.refocus', ' skin.bello', ' skin.nebula', ' skin.blackglassnova', ' skin.1080xf', ' skin.rapier', ' skin.titan', ' skin.box', ' skin.back-row', ' skin.maximinimalism', ' skin.transparency', ' skin.conq', ' skin.sio2']

SKINS_XMLS = ('script-hdhomerun-view-overlay.xml','script-hdhomerun-view-channel_entry.xml')
FONTS = ('font10','font13','font30')

VERSION = util.ADDON.getAddonInfo('version')
VERSION_FILE = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','version')

def copyTree(source,target):
	pct = 0
	mod = 5
	if not source or not target: return
	if not os.path.isdir(source): return
	sourcelen = len(source)
	if not source.endswith(os.path.sep): sourcelen += 1
	for path, dirs, files in os.walk(source): #@UnusedVariable
		subpath = path[sourcelen:]
		xbmcvfs.mkdir(os.path.join(target,subpath))
		for f in files:
			xbmcvfs.copy(os.path.join(path,f),os.path.join(target,subpath,f))
			pct += mod
			if pct > 100:
				pct = 95
				mod = -5
			elif pct < 0:
				pct = 5
				mod = 5

def currentKodiSkin():
    skinPath = xbmc.translatePath('special://skin').rstrip('/\\')
    return os.path.basename(skinPath)

def setupDynamicSkin():
    import shutil
    targetDir = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','resources')
    target = os.path.join(targetDir,'skins')

    if os.path.exists(target):
        shutil.rmtree(target,True)
    if not os.path.exists(targetDir): os.makedirs(targetDir)

    source = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'),'resources','skins')
    copyTree(source,target)

def customizeSkinXML(skin,xml):
    source = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('path')).decode('utf-8'),'resources','skins','Main','1080i',xml)
    target = os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin','resources','skins','Main','1080i',xml)
    with open(source,'r') as s:
        data = s.read()

    for font in FONTS:
        data = data.replace(font,'@{0}@'.format(font))
    for font in FONTS:
        data = data.replace('@{0}@'.format(font),FONT_TRANSLATIONS[skin][font])

    with open(target,'w') as t:
        t.write(data)

def updateNeeded():
    if not os.path.exists(VERSION_FILE): return True
    with open(VERSION_FILE, 'r') as f:
        version = f.read()
    if version != '{0}:{1}'.format(currentKodiSkin(),VERSION): return True
    return False

def getSkinPath():
    skin = currentKodiSkin()
    default = util.ADDON.getAddonInfo('path')
    if skin == 'skin.confluence': return default
    if not skin in FONT_TRANSLATIONS: return default
    if updateNeeded():
        util.DEBUG_LOG('Updating custom skin')
        try:
            setupDynamicSkin()
            for xml in SKINS_XMLS:
                customizeSkinXML(skin,xml)
            with open(VERSION_FILE, 'w') as f:
                f.write('{0}:{1}'.format(currentKodiSkin(),VERSION))
        except:
            util.ERROR()
            return default

    util.DEBUG_LOG('Using custom fonts for: {0}'.format(skin))

    return os.path.join(xbmc.translatePath(util.ADDON.getAddonInfo('profile')).decode('utf-8'),'skin')
