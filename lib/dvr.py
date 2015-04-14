# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import kodigui
import hdhr
import skin

import util

class RecordDialog(kodigui.BaseDialog):
    EPISODE_LIST = 201
    RECORD_BUTTON = 203
    def __init__(self,*args,**kwargs):
        kodigui.BaseDialog.__init__(self,*args,**kwargs)
        self.seriesID = kwargs.get('series_id')
        self.storageServer = kwargs.get('storage_server')
        self.results = kwargs.get('results')
        self.ruleAdded = False

    def onFirstInit(self):
        self.episodeList = kodigui.ManagedControlList(self,self.EPISODE_LIST,20)
        self.fillEpisodeList()

    def onAction(self,action):
        if action == xbmcgui.ACTION_CONTEXT_MENU:
            if self.getFocusId() == self.EPISODE_LIST:
                self.add()

        kodigui.BaseDialog.onAction(self,action)

    def onClick(self,controlID):
        if controlID == self.RECORD_BUTTON:
            self.add()

    def fillEpisodeList(self):
        items = []
        for r in self.results:
            if not r.seriesID == self.seriesID: continue
            item = kodigui.ManagedListItem(r.episodeTitle,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',r.seriesTitle)
            item.setProperty('episode.number',r.episodeNumber)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('air.date',r.displayDate())
            item.setProperty('air.time',r.displayTime())
            item.setProperty('original.date',r.displayDate(original=True))
            item.setProperty('original.time',r.displayTime(original=True))
            items.append(item)

        self.episodeList.addItems(items)

    def add(self):
        item = self.episodeList.getSelectedItem()
        if not item: return
        self.storageServer.addRule(item.dataSource)
        xbmcgui.Dialog().ok('Done','Recording rule added for:','',item.dataSource.seriesTitle)
        self.ruleAdded = True
        self.doClose()

class DVRBase():
    RECORDING_LIST_ID = 101
    SEARCH_PANEL_ID = 201
    RULE_LIST_ID = 301
    WATCH_BUTTON = 103
    SEARCH_BUTTON = 203
    RULES_BUTTON = 303

    def __init__(self,*args,**kwargs):
        self._BASE.__init__(self,*args,**kwargs)
        self.started = False
        self.recordingList = None
        self.searchPanel = None
        self.ruleList = None
        self.searchTerms = ''
        self.play = None
        self.searchResults = []
        self.devices = kwargs.get('devices')
        self.storageServer = hdhr.storageservers.StorageServers(self.devices)
        self.lineUp = kwargs.get('lineup')
        self.mode = 'WATCH'
        util.setGlobalProperty('NO_RESULTS','NO SEARCH RESULTS')
        util.setGlobalProperty('NO_RECORDINGS','NO RECORDINGS')

    @property
    def mode(self):
        return util.getGlobalProperty('DVR_MODE')

    @mode.setter
    def mode(self,val):
        util.setGlobalProperty('DVR_MODE',val)

    def onFirstInit(self):
        if self.recordingList:
            self.recordingList.reInit(self,self.RECORDING_LIST_ID)
        else:
            self.recordingList = kodigui.ManagedControlList(self,self.RECORDING_LIST_ID,10)
            self.fillRecordings()

        self.searchPanel = kodigui.ManagedControlList(self,self.SEARCH_PANEL_ID,6)
        self.fillSearchPanel()

        self.ruleList = kodigui.ManagedControlList(self,self.RULE_LIST_ID,10)
        self.fillRules()

        if self.recordingList.size():
            self.setFocusId(self.RECORDING_LIST_ID)
        else:
            self.setMode('SEARCH')

    def onAction(self,action):
        if action == xbmcgui.ACTION_GESTURE_SWIPE_LEFT:
            if self.mode == 'SEARCH':
                return self.setMode('RULES')
            elif self.mode == 'WATCH':
                return self.setMode('SEARCH')
        elif action == xbmcgui.ACTION_GESTURE_SWIPE_RIGHT:
            if self.mode == 'SEARCH':
                return self.setMode('WATCH')
            elif self.mode == 'RULES':
                return self.setMode('SEARCH')
        elif action == xbmcgui.ACTION_CONTEXT_MENU:
            if self.getFocusId() == self.RULE_LIST_ID:
                return self.doRuleContext()
            elif xbmc.getCondVisibility('ControlGroup(200).HasFocus(0)'):
                return self.setSearch()

        self._BASE.onAction(self,action)

    def onClick(self,controlID):
        if controlID == self.RECORDING_LIST_ID:
            item = self.recordingList.getSelectedItem()
            self.play = item.dataSource.playURL
            self.doClose()
        elif controlID == self.SEARCH_PANEL_ID:
            self.openRecordDialog()
        elif controlID == self.RULE_LIST_ID:
            self.doRuleContext()
        elif controlID == self.WATCH_BUTTON:
            self.setMode('WATCH')
        elif controlID == self.SEARCH_BUTTON:
            if self.mode == 'SEARCH':
                self.setSearch()
            self.setMode('SEARCH')
        elif controlID == self.RULES_BUTTON:
            self.setMode('RULES')

    def onFocus(self,controlID):
        if xbmc.getCondVisibility('ControlGroup(100).HasFocus(0)'):
            self.mode = 'WATCH'
        elif xbmc.getCondVisibility('ControlGroup(200).HasFocus(0)'):
            self.mode = 'SEARCH'
        elif xbmc.getCondVisibility('ControlGroup(300).HasFocus(0)'):
            self.mode = 'RULES'

    def setMode(self,mode):
        self.mode == mode
        if mode == 'WATCH':
            self.setFocusId(100)
        elif mode == 'SEARCH':
            self.setFocusId(200)
        elif mode == 'RULES':
            self.setFocusId(301)


    def fillRecordings(self):
        items = []
        for r in self.storageServer.recordings:
            item = kodigui.ManagedListItem(r.episodeTitle,r.synopsis,thumbnailImage=r.icon,data_source=r)
            item.setProperty('series.title',r.seriesTitle)
            item.setProperty('episode.number',r.episodeNumber)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('air.date',r.displayDate())
            item.setProperty('air.time',r.displayTime())
            items.append(item)

        util.setGlobalProperty('NO_RECORDINGS',not items and 'NO RECORDINGS' or '')
        self.recordingList.addItems(items)

    def fillSearchPanel(self):
        items = []
        series = {}
        self.searchResults = hdhr.guide.search(self.devices.apiAuthID(),terms=self.searchTerms) or []
        util.setGlobalProperty('NO_RESULTS',not self.searchResults and 'NO SEARCH RESULTS' or '')

        for r in self.searchResults:
            if r.seriesID in series:
                series[r.seriesID][1] += 1
                series[r.seriesID][0].setProperty('episode.count',str(series[r.seriesID][1]))
                continue
            item = kodigui.ManagedListItem(r.episodeTitle,r.synopsis,thumbnailImage=r.icon,data_source=r)
            series[r.seriesID] = [item,1]
            item.setProperty('series.title',r.seriesTitle)
            item.setProperty('episode.number',r.episodeNumber)
            item.setProperty('channel.number',r.channelNumber)
            item.setProperty('channel.name',r.channelName)
            item.setProperty('channel.icon',r.channelIcon)
            item.setProperty('air.date',r.displayDate())
            item.setProperty('air.time',r.displayTime())
            items.append(item)

        self.searchPanel.reset()
        self.searchPanel.addItems(items)

    def fillRules(self,update=False):
        if update: self.storageServer.updateRules()
        items = []
        for r in self.storageServer.rules:
            item = kodigui.ManagedListItem(r.title,str(r.priority),data_source=r)
            item.setProperty('rule.recent_only',r.recentOnly and 'RECENT' or 'ALWAYS')
            items.append(item)

        self.ruleList.reset()
        self.ruleList.addItems(items)

    def doRuleContext(self):
        item = self.ruleList.getSelectedItem()
        options = ['Toggle Recent Only','Set Priority','Delete']
        idx = xbmcgui.Dialog().select('Options',options)
        if idx < 0: return
        if idx == 0:
            item.dataSource.recentOnly = not item.dataSource.recentOnly
            item.setProperty('rule.recent_only',item.dataSource.recentOnly and 'RECENT' or 'ALWAYS')
        elif idx == 1:
            priority = xbmcgui.Dialog().input('Enter Priority',str(item.dataSource.priority))
            try:
                item.dataSource.priority = int(priority)
                item.setLabel2(str(item.dataSource.priority))
            except ValueError:
                return
        elif idx == 2:
            if self.storageServer.deleteRule(item.dataSource):
                self.ruleList.removeItem(item.pos())

    def setSearch(self):
        self.searchTerms = xbmcgui.Dialog().input('Enter search terms',self.searchTerms)
        self.setProperty('search.terms',self.searchTerms)
        self.fillSearchPanel()
        if not self.searchResults:
            self.setFocusId(202)
        else:
            self.setFocusId(201)

    def openRecordDialog(self):
        item = self.searchPanel.getSelectedItem()
        if not item: return
        path = skin.getSkinPath()
        d = RecordDialog(skin.DVR_RECORD_DIALOG,path,'Main','1080i',series_id=item.dataSource.seriesID,storage_server=self.storageServer,results=self.searchResults)
        d.doModal()
        if d.ruleAdded:
            self.fillRules(update=True)
        del d

class DVRWindow(DVRBase,kodigui.BaseWindow):
    _BASE = kodigui.BaseWindow

class DVRDialog(DVRBase,kodigui.BaseDialog):
    _BASE = kodigui.BaseDialog