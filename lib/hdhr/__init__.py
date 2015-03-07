# -*- coding: utf-8 -*-
import requests
import discovery
import ordereddict

def chanTuple(guide_number):
    major, minor = guide_number.split('.')
    return (int(major),int(minor))

class Channel(object):
    def __init__(self,data):
        self.number = data['GuideNumber']
        self.name = data['GuideName']
        self.urls = [data['URL']]
        self.favorite = bool(data.get('Favorite',False))


    def add(self,data):
        self.urls.append(data['url'])

class LineUp(object):
    def __init__(self):
        self.channels = ordereddict.OrderedDict()
        self.collectLineUp()

    def __getitem__(self,key):
        return self.channels[key]

    def indexed(self,index):
        return self.channels[[k for k in self.channels.keys()][index]]

    def collectLineUp(self):
        responses = discovery.discover(discovery.TUNER_DEVICE)
        lineUps = []

        for r in responses:
            lineUps.append(requests.get(r.url).json())

        while True:
            lowest = min(lineUps,key=lambda l: l and chanTuple(l[0]['GuideNumber']) or (0,0))
            if not lowest: return
            chanData = lowest.pop(0)
            if chanData['GuideNumber'] in self.channels:
                self.channels[chanData['GuideNumber']].add(chanData)
            else:
                self.channels[chanData['GuideNumber']] = Channel(chanData)