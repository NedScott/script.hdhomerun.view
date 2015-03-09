# -*- coding: utf-8 -*-
import xbmc, xbmcgui

import hdhr
import util

class OverlayPlayer(xbmc.Player):
    def init(self,overlay_dialog):
        self.overlayDialog = overlay_dialog
        return self

    def onPlayBackStopped(self):
        self.overlayDialog.close()

    def playChannel(self,channel,guideChannel):
        url = channel.sources[0].url
        currentShow = guideChannel.currentShow()
        title = currentShow.title or channel.name
        item = xbmcgui.ListItem(title,thumbnailImage=currentShow.icon)
        info = {'Title': title,
                'Plot':currentShow.synopsis,
                #'Studio':'{0} ({1})'.format(program.network,program.channelName)
        }
        item.setInfo('video', info)
        util.setSetting('last.channel',channel.number)
        self.play(url,item,False,0)

class BaseDialog(xbmcgui.WindowXMLDialog):
    def __init__(self,*args,**kwargs):
        self._closing = False
        self._winID = ''

    def onInit(self):
        self._winID = xbmcgui.getCurrentWindowDialogId()

    def setProperty(self,key,value):
        if self._closing: return
        xbmcgui.Window(self._winID).setProperty(key,value)
        xbmcgui.WindowXMLDialog.setProperty(self,key,value)

    def doClose(self):
        self._closing = True
        self.close()

    def onClosed(self): pass

class GuideOverlay(BaseDialog):
    def __init__(self,*args,**kwargs):
        BaseDialog.__init__(self,*args,**kwargs)
        self.started = False
        self.lineUp = None
        self.guide = None
        self.player = OverlayPlayer().init(self)

    def onInit(self):
        BaseDialog.onInit(self)
        if self.started: return
        self.started = True
        self.channelList = self.getControl(201)
        self.start()

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                self.showOverlay(False)
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return
                xbmc.executebuiltin('Action(back)')
            elif action == xbmcgui.ACTION_BUILT_IN_FUNCTION:
                xbmc.executebuiltin('ActivateWindow(12901)')
        except:
            util.ERROR()
            BaseDialog.onAction(self,action)
            return
        BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        pos = self.channelList.getSelectedPosition()
        channel = self.lineUp.indexed(pos)
        self.playChannel(channel)

    def closeHandler(self):
        if self.overlayVisible():
            self.showOverlay(False)
            return True
        else:
            return False
#        if xbmc.getCondVisibility('Player.HasVideo'):
#            self.fullscreenVideo()
#            return True

    def fullscreenVideo(self):
        if util.videoIsPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def getLineup(self):
        self.lineUp = hdhr.LineUp()
        last = util.getSetting('last.channel')
        items = []
        for channel in self.lineUp.channels.values():
            guideChan = self.guide.getChannel(channel.number)
            currentShow = guideChan.currentShow()
            title = channel.name
            thumb = currentShow.icon
            icon = guideChan.icon
            if icon: title = u'{0}: {1}'.format(channel.number,title)
            item = xbmcgui.ListItem(title,thumbnailImage=thumb)
            item.setProperty('channel.icon',icon)
            item.setProperty('channel.number',channel.number)
            item.setProperty('show.next',u'Next: {0}'.format(guideChan.nextShow().title or '(No Data)'))
            if last == channel.number:
                item.setProperty('is.current','true')
            prog = currentShow.progress()
            if prog != None:
                prog = int(prog - (prog % 5))
                item.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))
            items.append(item)
        self.channelList.addItems(items)

    def getGuide(self):
        self.guide = hdhr.Guide()

    def getStartChannel(self):
        last = util.getSetting('last.channel')
        if last and last in self.lineUp:
            return self.lineUp[last]
        else:
            return self.lineUp.indexed(0)

    def start(self):
        self.getGuide()
        self.getLineup()

        channel = self.getStartChannel()

        if util.videoIsPlaying():
            self.fullscreenVideo()
        else:
            self.playChannel(channel)
        pos = self.lineUp.index(channel.number)
        if pos > -1: self.channelList.selectItem(pos)

    def showOverlay(self,show=True):
        self.setProperty('show.overlay',show and 'SHOW' or '')

    def overlayVisible(self):
        return bool(self.getProperty('show.overlay'))

    def playChannel(self,channel):
        self.player.playChannel(channel,self.guide.getChannel(channel.number))
        self.fullscreenVideo()

def start():
    window = GuideOverlay('script-hdhomerun-view-overlay.xml',util.ADDON.getAddonInfo('path'),'Main','1080i')
    window.doModal()
    del window
