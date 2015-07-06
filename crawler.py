#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import os
import subprocess
import threading
import signal
import time
import re
import sys
import feedparser
from interruptingcow import timeout
from urlparse import urlparse
from readability.readability import Document
from datetime import date

import bson

from Queue import Queue
from pymongo import MongoClient

##############################################
# TODOS
# more metadata from rss
# get all urls from feeds, randomize then process
# might be more efficient and safe
# extract new urls and feeds from page

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
    def __init__(self, db = 'crawler', num_thread = 20):
        self.connect_db(db)
        self.feed_queue = Queue()
        self.url_queue = Queue()
        self.num_thread = num_thread


    def connect_db(self, db):
        client = MongoClient()
        self.blacklist = client[db]['blacklist']
        self.feeds = client[db]['feeds']
        self.urls = client[db]['urls']
        self.texts = client[db]['texts']


    def init_feed_statistics(self, feed):
        self.feeds.insert_one({'feed': feed, 'success': 0, 'fail': 0})

    def log_url(self, url, success = True):
        self.urls.insert_one({'url': url, 'success': success})

    def log_feed(self, feed, success = True):
        if success:
            self.feeds.update({'feed': feed}, {'$inc': {'success': 1}})
        else:
            self.feeds.update({'feed': feed}, {'$inc': {'fail': 1}})            

    # NEEDS IMPROVEMENT!!!
    # SOFT BAN
    def ban(self, url, feed):
        # site = urlparse(url).netloc
        # self.blacklist.insert_one({'site': site})
        self.blacklist.insert_one({'url': url, 'feed': feed})

    def is_valid(self, url):
        """
        check if the url is already processed or the site is banned
        """
        try:
            if not url:
                return False
            # site = urlparse(url).netloc
            if self.blacklist.find_one({'url': url}):
                return False
            if self.urls.find_one({'url': url}):
                return False
            return True
        except:
            return False

    def read_feeds(self, feeds_file):
        """
        read the initial feeds from the file
        save them into db
        """
        for line in open(feeds_file):
            feed = line.strip()
            if feed and not self.feeds.find_one({'feed': feed}):
                self.init_feed_statistics(feed)


    def get_plain_text(self, url, feed, entry):
        """
        get plain text from a given url by stacking two tools:
        1. get summary of the web page using readability
        2. get plain text from the html using lynx
        """
        min_length = 500
        max_length = 50000
        try:
            # with timeout(4, exception=RuntimeError):
            # suppose readability will not run forever, or we are in trouble
            title = entry.get('title')
            html = urllib.urlopen(url).read() # unknown encoding, readability will guess
            article = Document(html).summary() # unicode
            article = sub_ms_chars(article).encode('utf-8', 'ignore') # utf-8
            cmd = "lynx -dump -nolist -nomargins -nomore -stdin" # play with other parameters
            lynx = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
            t = threading.Timer(2, kill_lynx, args=[lynx.pid])
            t.start()
            text = lynx.communicate(input=article)[0] # utf-8, contains unknown character "?"
            # text = clean_lynx(text) # utf-8
            t.cancel()
            # length within boundary
            if min_length < len(text) < max_length:
                print title
                self.texts.insert_one({'title': title,\
                                       'text': bson.Binary(text),\
                                       'html': bson.Binary(article),\
                                       'url': url,\
                                       'feed': feed,\
                                       'date': str(date.today())}) # label, etc.
                return True
            else:
                return False
        except:
            # too strict?
            # try a soft ban: if 10 articles from the same site fails then ban the site
            self.ban(url, feed)
            # print 'ban!'
            return False

    def process_url(self):
        """
        multi-threading worker function
        process a single url
        """
        while True:
            feed, entry = self.url_queue.get()
            url = entry.get('link')
            if self.is_valid(url):
                # make sure no runtime error here
                success = self.get_plain_text(url, feed, entry)
                self.log_url(url, success) # only log if url is valid
            # report task done to queue
            self.url_queue.task_done()



    def get_rss_entries(self, feed):
        try:
            with timeout(1, exception=RuntimeError):
                rss = feedparser.parse(feed)
                if rss.status == 200:
                    return rss.entries
        except:
            return []

    def find_feed(self, url):
        return None

    def find_url(self, url):
        return None    


    def process(self):
        """
        main function:
        read feeds to be processed into a queue
        for each feed, process the urls with multi-threading 
        feeds are sequentially processed, easier to manage
        TODO: add new feeds and urls from the web page into the queue
        """
        for entry in self.feeds.find():
            self.feed_queue.put(entry['feed'])

        # set up workers
        for i in range(self.num_thread):
            worker = threading.Thread(target=self.process_url, args=())
            worker.setDaemon(True)
            worker.start()

        while not self.feed_queue.empty():
            feed = self.feed_queue.get()
            print 'feed',  feed

            entries = self.get_rss_entries(feed)
            if entries:
                self.log_feed(feed, True)
                for entry in entries:
                    self.url_queue.put((feed, entry))
            else:
                self.log_feed(feed, False)
            self.url_queue.join()



##############################################
if __name__ == '__main__':
    crawler = Crawler()
    crawler.read_feeds('feeds.txt')
    crawler.process()

