# -*- coding: utf-8 -*-
import requests
import urllib
import guide
from lib import util

MY = 'mytest'
#RECORDING_RULES_URL = 'http://%s.hdhomerun.com/api/recording_rules?DeviceAuth={0}&random={1}' % MY
RECORDING_RULES_URL = 'http://%s.hdhomerun.com/api/recording_rules?DeviceAuth={0}' % MY
MODIFY_RULE_URL = 'http://%s.hdhomerun.com/api/recording_rules?DeviceAuth={deviceAuth}&Cmd={cmd}&SeriesID={seriesID}&Title={title}&RecentOnly={recentOnly}&Priority={priority}' % MY

class RecordingRule(dict):
    @property
    def seriesID(self):
        return self.get('SeriesID')

    @property
    def title(self):
        return self.get('Title','')

    @property
    def recentOnly(self):
        return bool(self.get('RecentOnly'))

    @recentOnly.setter
    def recentOnly(self,val):
        if self.get('RecentOnly') == val: return
        self['RecentOnly'] = val and 1 or 0
        self.modify()

    @property
    def priority(self):
        return self.get('Priority',0)

    @priority.setter
    def priority(self,val):
        if self.get('Priority') == val: return
        self['Priority'] = val
        self.modify()

    def init(self,storage_server,add=False):
        self['STORAGE_SERVER'] = storage_server
        if add: return self.modify()
        return self

    def modify(self):
        url = MODIFY_RULE_URL.format(
            deviceAuth=self['STORAGE_SERVER']._devices.apiAuthID(),
            cmd='add',
            seriesID=self.seriesID,
            title=urllib.quote(self.title),
            recentOnly=self.get('RecentOnly') or 0,
            priority=self.priority
        )
        util.DEBUG_LOG('Modifying rule: {0}'.format(url))
        req = requests.get(url)
        util.DEBUG_LOG('Rule mod response: {0}'.format(repr(req.text)))
        return self

    def delete(self):
        url = MODIFY_RULE_URL.format(
            deviceAuth=self['STORAGE_SERVER']._devices.apiAuthID(),
            cmd='delete',
            seriesID=self.seriesID,
            title='',
            recentOnly='',
            priority=''
        )
        util.DEBUG_LOG('Deleting rule: {0}'.format(url))
        req = requests.get(url)
        util.DEBUG_LOG('Rule delete response: {0}'.format(repr(req.text)))
        return self

#"ChannelAffiliate":"CBS",
#"ChannelImageURL":"http://my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Station.svc/2/765/Logo/120x120",
#"ChannelName":"KIRO-DT",
#"ChannelNumber":"7.1",
#"EndTime":"1428638460",
#"EpisodeNumber":"106",
#"EpisodeTitle":"Heal Thyself",
#"ImageURL":"http://my.hdhomerun.com/fyimediaservices/v_3_3_6_1/Program.svc/96/2111966/Primary",
#"OriginalAirdate":"1428537600",
#"ProgramID":"11920222",
#"SeriesID":"11920222",
#"StartTime":"1428636660",
#"Synopsis":"While at a doctor's visit, Oscar decides to pursue Felix's physician, Sharon, but winds up inadvertently kicking Felix's hypochondria into high gear.",
#"Title":"The Odd Couple",
#"PlayURL":"http://192.168.1.24:40172/play?id=1a7249c1"


class Recording(guide.SearchResult):
    @property
    def playURL(self):
        return self.get('PlayURL','')

class StorageServers(object):
    def __init__(self,devices):
        self._devices = devices
        self._recordings = []
        self._rules = []
        self._init()

    def _init(self):
        self._getRecordings()
        self._getRules()

    def _getRecordings(self):
        self._recordings = []
        for d in self._devices.storageServers:
            try:
                recs = d.recordings()
                if recs: self._recordings += [Recording(r) for r in recs]
            except:
                util.ERROR()

    def _getRules(self):
        url = RECORDING_RULES_URL.format(self._devices.apiAuthID())
        util.DEBUG_LOG('Getting recording rules: {0}'.format(url))
        #req = requests.get(url,headers={'Cache-Control':'no-cache'})
        req = requests.get(url)
        self._rules = [RecordingRule(r).init(self) for r in req.json()]

    @property
    def recordings(self):
        return self._recordings

    @property
    def rules(self):
        return self._rules

    def updateRecordings(self):
        self._getRecordings()

    def updateRules(self):
        self._getRules()

    def deleteRule(self,rule):
        if not rule in self._rules: return False

        self._rules.pop(self._rules.index(rule.delete()))
        return True

    def addRule(self,result):
        self._rules.append(RecordingRule(result).init(self,add=True))