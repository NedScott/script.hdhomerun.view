# -*- coding: utf-8 -*-
import time
import xbmc, xbmcgui

import hdhr
import kodigui
import util

MAX_TIME_INT = 31536000000 #1000 years from Epoch

class PlayerStatus(object):
    def __init__(self):
        self.reset()

    def __eq__(self,val):
        return self.status == val

    def __ne__(self,val):
        return self.status != val

    def __call__(self,status,channel=None,item=None):
        if channel:
            self.channel = channel
            self.item = item
        else:
            if not self.channel:
                return
        self.status = status

    def reset(self):
        self.status = None
        self.index = 0
        self.channel = None
        self.item = None

    def nextSource(self):
        if not self.channel: return None
        self.index += 1
        if len(self.channel.sources) <= self.index: return None
        return self.channel.sources[self.index]

class ChannelPlayer(xbmc.Player):
    def init(self,overlay_dialog):
        self.status = PlayerStatus()

        self.overlayDialog = overlay_dialog
        return self

    def onPlayBackStarted(self):
        self.status('STARTED')
        self.overlayDialog.onPlayBackStarted()

    def onPlayBackStopped(self):
        if self.status == 'NOT_STARTED':
            if self.onPlayBackFailed(): return
        self.overlayDialog.onPlayBackStopped()
        self.status.reset()

    def onPlayBackEnded(self):
        if self.status == 'NOT_STARTED':
            if self.onPlayBackFailed(): return
        self.overlayDialog.onPlayBackEnded()
        self.status.reset()

    def onPlayBackFailed(self):
        source = self.status.nextSource()
        if source:
            util.DEBUG_LOG('Playing from NEXT source: {0}'.format(source.ID))
            self.play(source.url,self.item,False,0)
            return True
        else:
            self.status.reset()
            self.overlayDialog.onPlayBackFailed()
            return False

    def playChannel(self,channel):
        url = channel.sources[0].url
        util.DEBUG_LOG('Playing from source: {0}'.format(channel.sources[0].ID))
        currentShow = channel.guide.currentShow()
        title = currentShow.title or channel.name
        item = xbmcgui.ListItem(title,thumbnailImage=currentShow.icon)
        info = {'Title': title,
                'Plot':currentShow.synopsis,
                #'Studio':'{0} ({1})'.format(program.network,program.channelName)
        }
        item.setInfo('video', info)
        util.setSetting('last.channel',channel.number)
        self.status('NOT_STARTED',channel,item)
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

class GuideOverlay(BaseDialog,util.CronReceiver):
    def __init__(self,*args,**kwargs):
        BaseDialog.__init__(self,*args,**kwargs)
        self.started = False
        self.lineUp = None
        self.guide = None
        self.current = None
        self.nextGuideUpdate = MAX_TIME_INT
        self.player = ChannelPlayer().init(self)

    def onInit(self):
        BaseDialog.onInit(self)
        if self.started: return
        self.started = True
        self.channelList = kodigui.ManagedControlList(self,201,3)
        self.start()

    def onAction(self,action):
        try:
            if action == xbmcgui.ACTION_CONTEXT_MENU or action == xbmcgui.ACTION_MOVE_RIGHT or action == xbmcgui.ACTION_MOVE_UP or action == xbmcgui.ACTION_MOVE_DOWN:
                self.showOverlay()
            elif action == xbmcgui.ACTION_MOVE_LEFT:
                self.showOverlay(False)
            elif action == xbmcgui.ACTION_PREVIOUS_MENU or action == xbmcgui.ACTION_NAV_BACK:
                if self.closeHandler(): return
                if xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'): xbmc.executebuiltin('Action(back)')
            elif action == xbmcgui.ACTION_BUILT_IN_FUNCTION:
                self.showOverlay(False)
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

    def updateProgressBars(self):
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
            if icon: title = u'[COLOR FF99CCFF]{0}[/COLOR] {1}'.format(mli.dataSource.number,title)
            mli.setLabel(title)
            mli.setThumbnailImage(thumb)
            mli.setProperty('show.title',currentShow.title)
            mli.setProperty('show.synopsis',currentShow.synopsis)
            mli.setProperty('next.title',u'Next: {0}'.format(nextShow.title or '(No Data)'))
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
        if not mli: return
        self.current = mli
        self.current.setProperty('is.current','true')

    def closeHandler(self):
        if self.overlayVisible():
            if not self.player.isPlaying():
                return False
            self.showOverlay(False)
            return True
        else:
            return False

    def fullscreenVideo(self):
        if util.videoIsPlaying():
            xbmc.executebuiltin('ActivateWindow(fullscreenvideo)')

    def getLineUpAndGuide(self):
        self.lineUp = hdhr.LineUp()
        self.showProgress(50,'Fetching Guide')
        self.updateGuide()
        self.showProgress(75,'Finishing Up')

    def updateGuide(self):
        guide = hdhr.Guide()
        self.nextGuideUpdate = MAX_TIME_INT
        for channel in self.lineUp.channels.values():
            guideChan = guide.getChannel(channel.number)
            channel.setGuide(guideChan)
            if channel.guide:
                end = channel.guide.currentShow().end
                if end and end < self.nextGuideUpdate:
                    self.nextGuideUpdate = end
        util.DEBUG_LOG('Next guide update: {0} minutes'.format(int((self.nextGuideUpdate - time.time())/60)))

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
            if icon: title = u'[COLOR FF99CCFF]{0}[/COLOR] {1}'.format(channel.number,title)
            item = kodigui.ManagedListItem(title,thumbnailImage=thumb,data_source=channel)
            item.setProperty('channel.icon',icon)
            item.setProperty('channel.number',channel.number)
            item.setProperty('show.title',currentShow.title)
            item.setProperty('show.synopsis',currentShow.synopsis)
            item.setProperty('next.title',u'Next: {0}'.format(nextShow.title or '(No Data)'))
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
        self.getLineUpAndGuide()
        self.fillChannelList()

        channel = self.getStartChannel()

        if self.player.isPlaying():
            self.fullscreenVideo()
            self.showProgress()
        else:
            self.playChannel(channel)
        pos = self.lineUp.index(channel.number)
        if pos > -1: self.channelList.selectItem(pos)

        self.cron.registerReceiver(self)

        for d in self.lineUp.devices.values():
            util.DEBUG_LOG('Device: {0} at {1} with {2} channels'.format(d.ID,d.ip,d.channelCount))

    def showProgress(self,progress='',message=''):
        self.setProperty('loading.progress',str(progress))
        self.setProperty('loading.status',message)

    def showOverlay(self,show=True):
        self.setProperty('show.overlay',show and 'SHOW' or '')
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
