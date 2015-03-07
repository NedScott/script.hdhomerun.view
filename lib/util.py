# -*- coding: utf-8 -*-

DEBUG = True

def LOG(msg):
    print 'script.hdhomerun.view: {0}'.format(msg)

def DEBUG_LOG(msg):
    if not DEBUG: return
    LOG(msg)