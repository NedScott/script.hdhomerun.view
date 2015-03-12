# -*- coding: utf-8 -*-
import time
import xbmc, xbmcgui

import hdhr
import kodigui
import util
import player

MAX_TIME_INT = 31536000000 #1000 years from Epoch

CHANNEL_DISPLAY = u'[COLOR FF99CCFF]{0}[/COLOR] {1}'

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

class GuideOverlay(BaseDialog,util.CronReceiver):
    def __init__(self,*args,**kwargs):
        BaseDialog.__init__(self,*args,**kwargs)
        self.started = False
        self.lineUp = None
        self.guide = None
        self.current = None
        self.nextGuideUpdate = MAX_TIME_INT

    def onInit(self):
        BaseDialog.onInit(self)
        if self.started: return
        self.started = True
        self.channelList = kodigui.ManagedControlList(self,201,3)
        self.currentProgress = self.getControl(250)
        self.start()

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                self.showOverlay(False)
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return
            elif action == xbmcgui.ACTION_BUILT_IN_FUNCTION:
                self.showOverlay(False)
                xbmc.executebuiltin('ActivateWindow(12901)')
            elif action == xbmcgui.ACTION_SELECT_ITEM and not self.overlayVisible():
                xbmc.executebuiltin('ActivateWindow(12901)')
        except:
            util.ERROR()
            BaseDialog.onAction(self,action)
            return
        BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        mli = self.channelList.getSelectedItem()
        self.setCurrent(mli)
        channel = mli.dataSource
        self.playChannel(channel)

    def tick(self):
        if time.time() > self.nextGuideUpdate:
            self.updateChannels()
        else:
            self.updateProgressBars()

    def updateProgressBars(self,force=False):
        if not force and not self.overlayVisible(): return

        if self.current:
            self.currentProgress.setPercent(self.current.dataSource.guide.currentShow().progress() or 0)

        for mli in self.channelList:
            prog = mli.dataSource.guide.currentShow().progress()
            if prog == None:
                mli.setProperty('show.progress','')
            else:
                prog = int(prog - (prog % 5))
                mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))

    def updateChannels(self):
        util.DEBUG_LOG('Updating channels')
        self.updateGuide()
        for mli in self.channelList:
            guideChan = mli.dataSource.guide
            currentShow = guideChan.currentShow()
            nextShow = guideChan.nextShow()
            title = mli.dataSource.name
            thumb = currentShow.icon
            icon = guideChan.icon
            if icon: title = CHANNEL_DISPLAY.format(mli.dataSource.number,title)
            mli.setLabel(title)
            mli.setThumbnailImage(thumb)
            mli.setProperty('show.title',currentShow.title)
            mli.setProperty('show.synopsis',currentShow.synopsis)
            mli.setProperty('next.title',u'{0}: {1}'.format(util.T(32004),nextShow.title or util.T(32005)))
            mli.setProperty('next.icon',nextShow.icon)
            start = nextShow.start
            if start:
                mli.setProperty('next.start',time.strftime('%I:%M %p',time.localtime(start)))
            prog = currentShow.progress()
            if prog != None:
                prog = int(prog - (prog % 5))
                mli.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))

    def setCurrent(self,mli=None):
        if self.current:
            self.current.setProperty('is.current','')
            self.current = None
        if not mli: return self.setWinProperties()
        self.current = mli
        self.current.setProperty('is.current','true')
        self.setWinProperties()

    def closeHandler(self):
        if self.overlayVisible():
            if not self.player.isPlaying():
                return self.askExit()
            self.showOverlay(False)
            return True
        else:
            return self.askExit()

    def askExit(self):
        if not util.getSetting('confirm.exit'): return False
        if xbmcgui.Dialog().yesno(util.T(32006),'',util.T(32007),''):
            self.close()
            if xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'): xbmc.executebuiltin('Action(back)')
        return True


    def fullscreenVideo(self):
        if util.videoIsPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def getLineUpAndGuide(self):
        try:
            self.lineUp = hdhr.LineUp()
        except:
            e = util.ERROR()
            xbmcgui.Dialog().ok('Error','Unable to find tuners: ',e,'Click OK to exit.')
            return False

        self.showProgress(50,util.T(32008))
        self.updateGuide()
        self.showProgress(75,util.T(32009))
        return True

    def updateGuide(self):
        try:
            guide = hdhr.Guide(self.lineUp)
        except:
            e = util.ERROR()
            util.showNotification(e,header='Unable to fetch guide data')
            guide = hdhr.Guide()

        self.nextGuideUpdate = MAX_TIME_INT
        for channel in self.lineUp.channels.values():
            guideChan = guide.getChannel(channel.number)
            channel.setGuide(guideChan)
            if channel.guide:
                end = channel.guide.currentShow().end
                if end and end < self.nextGuideUpdate:
                    self.nextGuideUpdate = end
        self.setWinProperties()
        util.DEBUG_LOG('Next guide update: {0} minutes'.format(int((self.nextGuideUpdate - time.time())/60)))

    def setWinProperties(self):
        title = ''
        icon = ''
        nextTitle = ''
        progress = None
        channel = ''
        if self.current:
            channel = CHANNEL_DISPLAY.format(self.current.dataSource.number,self.current.dataSource.name)
            if self.current.dataSource.guide:
                currentShow = self.current.dataSource.guide.currentShow()
                title = currentShow.title
                icon = currentShow.icon
                progress = currentShow.progress()
                nextTitle = u'{0}: {1}'.format(util.T(32004),self.current.dataSource.guide.nextShow().title or util.T(32005))

        self.setProperty('show.title',title)
        self.setProperty('show.icon',icon)
        self.setProperty('next.title',nextTitle)
        self.setProperty('channel.name',channel)

        if progress != None:
            self.currentProgress.setPercent(progress)
            self.currentProgress.setVisible(True)
        else:
            self.currentProgress.setPercent(0)
            self.currentProgress.setVisible(False)

    def fillChannelList(self):
        last = util.getSetting('last.channel')
        items = []
        for channel in self.lineUp.channels.values():
            guideChan = channel.guide
            currentShow = guideChan.currentShow()
            nextShow = guideChan.nextShow()
            title = channel.name
            thumb = currentShow.icon
            icon = guideChan.icon
            if icon: title = CHANNEL_DISPLAY.format(channel.number,title)
            item = kodigui.ManagedListItem(title,thumbnailImage=thumb,data_source=channel)
            item.setProperty('channel.icon',icon)
            item.setProperty('channel.number',channel.number)
            item.setProperty('show.title',currentShow.title)
            item.setProperty('show.synopsis',currentShow.synopsis)
            item.setProperty('next.title',u'{0}: {1}'.format(util.T(32004),nextShow.title or util.T(32005)))
            item.setProperty('next.icon',nextShow.icon)
            start = nextShow.start
            if start:
                item.setProperty('next.start',time.strftime('%I:%M %p',time.localtime(start)))
            if last == channel.number:
                self.setCurrent(item)
            prog = currentShow.progress()
            if prog != None:
                prog = int(prog - (prog % 5))
                item.setProperty('show.progress','progress/script-hdhomerun-view-progress_{0}.png'.format(prog))
            items.append(item)
        self.channelList.addItems(items)

    def getStartChannel(self):
        last = util.getSetting('last.channel')
        if last and last in self.lineUp:
            return self.lineUp[last]
        else:
            return self.lineUp.indexed(0)

    def start(self):
        if not self.getLineUpAndGuide(): #If we fail to get lineUp, just exit
            self.close()
            return
        self.fillChannelList()

        self.player = player.ChannelPlayer().init(self,self.lineUp)

        channel = self.getStartChannel()

        if self.player.isPlayingHDHR():
            util.DEBUG_LOG('HDHR video already playing')
            self.fullscreenVideo()
            self.showProgress()
        else:
            util.DEBUG_LOG('HDHR video not currently playing. Starting channel...')
            self.playChannel(channel)

        pos = self.lineUp.index(channel.number)
        if pos > -1:
            self.channelList.selectItem(pos)
            mli = self.channelList.getListItem(pos)
            self.setCurrent(mli)

        self.cron.registerReceiver(self)

        for d in self.lineUp.devices.values():
            util.DEBUG_LOG('Device: {0} at {1} with {2} channels'.format(d.ID,d.ip,d.channelCount))

    def showProgress(self,progress='',message=''):
        self.setProperty('loading.progress',str(progress))
        self.setProperty('loading.status',message)

    def showOverlay(self,show=True):
        self.updateProgressBars()
        self.setProperty('show.overlay',show and 'SHOW' or '')
        if self.getFocusId() == 201: return
        self.setFocusId(201)

    def overlayVisible(self):
        return bool(self.getProperty('show.overlay'))

    def onPlayBackStarted(self):
        util.DEBUG_LOG('ON PLAYBACK STARTED')
        self.showProgress()

    def onPlayBackStopped(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK STOPPED')
        self.showProgress() #In case we failed to play video
        self.showOverlay()

    def onPlayBackFailed(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK FAILED')

    def onPlayBackEnded(self):
        self.setCurrent()
        util.DEBUG_LOG('ON PLAYBACK ENDED')

    def playChannel(self,channel):
        self.player.playChannel(channel)
        self.fullscreenVideo()

def start():
    window = GuideOverlay('script-hdhomerun-view-overlay.xml',util.ADDON.getAddonInfo('path'),'Main','1080i')
    with util.Cron(5) as window.cron:
        window.doModal()
        del window
