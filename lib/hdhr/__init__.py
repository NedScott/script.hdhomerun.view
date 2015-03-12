# -*- coding: utf-8 -*-
import time
import requests
import discovery
import ordereddict

from lib import util

GUIDE_URL = 'http://mytest.hdhomerun.com/api/guide.php?DeviceID={0}'

def chanTuple(guide_number,chanCount):
    major, minor = guide_number.split('.',1)
    return (int(major),int(minor),chanCount*-1)

class ChannelSource(dict):
    @property
    def url(self):
        return self['url']

    @property
    def ID(self):
        return self['ID']

class Channel(object):
    def __init__(self,data,device_response):
        self.number = data['GuideNumber']
        self.name = data['GuideName']
        self.sources = [ChannelSource({'url':data['URL'],'ID':device_response.ID})]
        self.favorite = bool(data.get('Favorite',False))
        self.guide = None

    def add(self,data,device_response):
        self.sources.append(ChannelSource({'url':data['URL'],'ID':device_response.ID}))

    def setGuide(self,guide):
        self.guide = guide

class LineUp(object):
    def __init__(self):
        self.channels = ordereddict.OrderedDict()
        self.devices = {}
        self.collectLineUp()
        self.hasGuideData = False

    def __getitem__(self,key):
        return self.channels[key]

    def __contains__(self, key):
        return key in self.channels

    def index(self,key):
        if not key in self.channels: return -1
        return self.channels.keys().index(key)

    def indexed(self,index):
        return self.channels[[k for k in self.channels.keys()][index]]

    def getDeviceByIP(self,ip):
        for d in self.devices.values():
            if d.ip == ip:
                return d
        return None

    def defaultDevice(self):
        #Return device with the most number of channels as default
        highest = None
        for d in self.devices.values():
            if not highest or highest.channelCount < d.channelCount:
                highest = d
        return highest

    def collectLineUp(self):
        responses = discovery.discover(discovery.TUNER_DEVICE)
        lineUps = []

        for r in responses:
            self.devices[r.ID] = r
            lineup = requests.get(r.url).json()
            r.channelCount = len(lineup)
            lineUps.append((r,lineup))

        while True:
            lowest = min(lineUps,key=lambda l: l[1] and chanTuple(l[1][0]['GuideNumber'],l[0].channelCount) or (0,0,0)) #Prefer devices with the most channels assuming (possibly wrongly) that they are getting a better signal
            if not lowest[1]: return
            chanData = lowest[1].pop(0)
            if chanData['GuideNumber'] in self.channels:
                self.channels[chanData['GuideNumber']].add(chanData,lowest[0])
            else:
                self.channels[chanData['GuideNumber']] = Channel(chanData,lowest[0])

class Show(dict):
    @property
    def title(self):
        return self.get('Title','')

    @property
    def epTitle(self):
        return self.get('EpisodeTitle','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def synopsis(self):
        return self.get('Synopsis','')

    @property
    def start(self):
        return self.get('StartTime')

    @property
    def end(self):
        return self.get('EndTime')

    def progress(self):
        start = self.get('StartTime')
        if not start: return None
        end = self.get('EndTime')
        duration = end - start
        sofar = time.time() - start
        return int((sofar/duration)*100)

class GuideChannel(dict):
    @property
    def number(self):
        return self.get('GuideNumber','')

    @property
    def name(self):
        return self.get('GuideName','')

    @property
    def icon(self):
        return self.get('ImageURL','')

    @property
    def affiliate(self):
        return self.get('Affiliate','')

    def currentShow(self):
        shows = self.get('Guide')
        if not shows: return Show()
        now = time.time()
        for s in shows:
            if now >= s.get('StartTime') and now < s.get('EndTime'):
                return Show(s)
        return Show()

    def nextShow(self):
        shows = self.get('Guide')
        if not shows: return Show()
        if len(shows) < 2: return Show()
        now = time.time()
        for i,s in enumerate(shows):
            if now >= s.get('StartTime') and now < s.get('EndTime'):
                i+=1
                if i >= len(shows): break
                return Show(shows[i])

        return Show()

class Guide(object):
    def __init__(self,lineup=None):
        self.init(lineup)

    def init(self,lineup):
        self.guide = ordereddict.OrderedDict()
        if not lineup:
            return
        url = GUIDE_URL.format(lineup.defaultDevice().ID)
        util.DEBUG_LOG('Fetching guide from: {0}'.format(url))
        data = requests.get(url).json()
        for chan in data:
            self.guide[chan['GuideNumber']] = chan

    def getChannel(self,guide_number):
        return GuideChannel(self.guide.get(guide_number) or {})