#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import os
import subprocess
import threading
import signal
import re
import sys
import feedparser
from interruptingcow import timeout
from urlparse import urlparse
from readability.readability import Document
from datetime import date

from Queue import Queue
import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

##############################################
# TODOS
# get links from processed pages
# even safer, subdir of date for each run
# combined with logging
# learn the parameters of lynx, very useful

##############################################
# helper

_LINK_BRACKETS = re.compile(r"\[\d+]", re.U)
_LEFT_BRACKETS = re.compile(r"\[", re.U)
_RIGHT_BRACKETS = re.compile(r"]", re.U)
_NEW_LINE = re.compile(r"([^\r\n])\r?\n([^\r\n])", re.U)
_SPECIAL_CHARS = re.compile(r"\f|\r|\t|_", re.U)
_WHITE_SPACE = re.compile(r" [ ]+", re.U)
 
MS_CHARS = {u"\u2018":"'",
            u"\u2019":"'",
            u"\u201c":"\"",
            u"\u201d":"\"",
            u"\u2020":"",
            u"\u2026":"",
            u"\u25BC":"",
            u"\u2665":""}
 
def clean_lynx(input):
 
    # for i in MS_CHARS.keys():
    #     input = input.replace(i,MS_CHARS[i])
 
    input = _NEW_LINE.sub("\g<1> \g<2>", input)
    input = _LINK_BRACKETS.sub("", input)
    input = _LEFT_BRACKETS.sub("(", input)
    input = _RIGHT_BRACKETS.sub(")", input)
    input = _SPECIAL_CHARS.sub(" ", input)
    input = _WHITE_SPACE.sub(" ", input)

    return input

def sub_ms_chars(text):
    for i in MS_CHARS.keys():
        text = text.replace(i,MS_CHARS[i])
    return text


def kill_lynx(pid):
    os.kill(pid, signal.SIGKILL)
    os.waitpid(-1, os.WNOHANG)
    print("lynx killed")

##############################################

class Crawler:
    def __init__(self, data_dir = 'data', db = 'crawler'):
        self.connect_db(db)
        self.data_dir = data_dir
        self.feed_queue = Queue()
        self.url_queue = Queue()
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.count = len(os.listdir(data_dir)) + 1

    def connect_db(self, db):
        client = MongoClient()
        self.blacklist = client[db]['blacklist']
        self.feeds = client[db]['feeds']
        self.urls = client[db]['urls']
        self.texts = client[db]['texts']

    def ban(self, url):
        site = urlparse(url).netloc
        self.blacklist.insert_one({'site': site})

    def is_valid(self, url):
        try:
            site = urlparse(url).netloc
            if self.blacklist.find_one({'site': site}):
                return False
            if self.urls.find_one({'url': url}):
                return False
            return True
        except:
            return False


    def read_feeds(self, feeds_file):
        """
        read the initial feeds from the file
        put them into the feed_queue
        for robustness, retrieve feed from db again
        """
        for line in open(feeds_file):
            feed = line.strip()
            if feed and not self.feeds.find_one({'feed': feed}):
                self.feeds.insert_one({'feed': feed, 'success': 0, 'fail': 0})



    def process_queue(self):
        """
        get urls of the feeds from feed_queue, put into url_queue
        process the urls from url_queue, add new urls and feads into corresponding queue
        update the success and fail count of the feed
        """
        for entry in self.feeds.find():
            self.feed_queue.put(entry['feed'])
        while not self.feed_queue.empty():
            feed = self.feed_queue.get()
            print feed
            urls = self.get_urls_and_titles(feed)            
            if urls:
                self.feeds.update({'feed': feed}, {'$inc': {'success': 1}})
                for (url, title) in urls:
                    self.url_queue.put((url, title))

                while not self.url_queue.empty():
                    url, title = self.url_queue.get()
                    print url
                    if self.is_valid(url):
                        filename = '%d.txt' % self.count
                        path = os.path.join(self.data_dir, filename)
                        flag, new_feeds, new_urls = self.get_plain_text(url, path)
                        if flag == 0:
                            self.urls.insert_one({'url': url, 'success': True})
                            self.texts.insert_one({'file': filename,\
                                                   'title': title,\
                                                   'url': url,\
                                                   'feed': feed,\
                                                   'date': str(date.today())})
                            self.count += 1
                            for new_feed in new_feeds:
                                self.feed_queue.put(new_feed)
                            for new_url in new_urls:
                                self.url_queue.put(new_url)

                        else:
                            self.urls.insert_one({'url': url, 'success': False})
                            self.ban(url)

            else:
                self.feeds.update({'feed': feed}, {'$inc': {'fail': 1}})


    def get_urls_and_titles(self, feed):
        urls = []
        try:
            with timeout(3, exception=RuntimeError):
                feed = feedparser.parse(feed)
                if feed.status == 200:
                    for entry in feed.entries:
                        # TODO: check if all RSS have .link, or something else 
                        link = entry.link
                        title = entry.title
                        urls.append((link, title))
        except:
            pass
        return urls

    def find_feed(self, url):
        return None

    def find_url(self, url):
        return None    


    def get_plain_text(self, url, output):
        """
        get plain text from a given url by stacking two tools:
        1. get summary of the web page using readability
        2. get plain text from the html using lynx
        """
        min_length = 500
        max_length = 50000        
        try:
            with timeout(4, exception=RuntimeError):
                html = urllib.urlopen(url).read()
                article = Document(html).summary()
                article = sub_ms_chars(article)
                cmd = "lynx -dump -nolist -notitle -stdin"
                lynx = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                t = threading.Timer(2, kill_lynx, args=[lynx.pid])
                t.start()            
                text = lynx.communicate(input=article.encode('utf-8'))[0]
                t.cancel()
                if min_length < len(text) < max_length:
                    f = open(output, 'w')
                    f.write(text)
                    f.close()
                    return 0, [], [] # success
                else:
                    return 1, [], [] # text too short or too long
        except:
            return 2, [], []

 

##############################################
if __name__ == '__main__':
    crawler = Crawler()
    crawler.read_feeds('feeds.txt')
    crawler.process_queue()

