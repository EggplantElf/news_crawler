#!/usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import os
import subprocess
import threading
import lynx
import re
import sys
import feedparser
from interruptingcow import timeout
from urlparse import urlparse
from readability.readability import Document

##############################################
# TODOS
# get links from processed pages
# dynamic index, depends on the number of files in the dir
# even safer, subdir of date for each run
# also sort by topic, keep a db for the attributes of the files
# incorporate mongodb, more POWERFUL control
# acoid write and read tmp.html for lynx, see if possible to direct pass text

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

# whole task includes:
# get news url from google news api (as the only url source, instead of from web page)
# manage the processed and blacklisted urls, domain name
# try:
#   pipeline to get plain text from url
# except:
#   blacklist the unresolvable domains
# store url respectively

class Crawler:
    def __init__(self, data_dir = 'data'):
        self.blacklist = set()
        self.load_seen()
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.count = len(os.listdir(data_dir)) + 1

    def load_seen(self):
        filename = 'processed.txt'
        self.seen = set()
        if not os.path.exists(filename):
            open(filename, 'a').close()
        for line in open(filename):
            self.seen.add(line.strip())

    def save_seen(self):
        f = open('processed.txt', 'a')
        for url in self.seen:
            f.write(url + '\n')
        f.close()

    def ban(self, url):
        site = urlparse(url).netloc
        self.blacklist.add(site)

    def is_valid(self, url):
        try:
            site = urlparse(url).netloc
            return site not in self.blacklist
        except:
            return False

    def show_blacklist(self):
        for site in self.blacklist:
            print site

    def process(self, feeds_file):
        source = self.get_source(feeds_file)
        print source
        self.crawl(source)
        self.save_seen()

    # with timeout
    def get_source(self, feeds_file):
        print 'getting URLs from feeds'
        source = []
        for line in open(feeds_file):
            url = line.strip()
            if url:
                try:
                    with timeout(3, exception=RuntimeError):
                        feed = feedparser.parse(url)
                        if feed.status == 200:
                            for entry in feed.entries:
                                link = entry.link
                                source.append(link)
                except:
                    continue
        return source


    def crawl(self, source):
        """
        save plain text from url source, which is the output of a feed 
        """
        print 'crawling...'
        for url in source:
            print url
            if self.is_valid(url) and url not in self.seen:
                self.seen.add(url)
                filename = os.path.join(self.data_dir, '%d.txt' % self.count)
                flag = self.pipeline(url, filename)
                if flag == 0:
                    self.count += 1
                elif flag == 2:
                    self.ban(url)
        # os.remove('tmp.html')



    def pipeline(self, url, output):
        """
        Pipeline to deal with one web page
        1. get summary of the web page
        2. get palin text from the html
        """
        min_length = 500
        max_length = 50000

        try:
            with timeout(3, exception=RuntimeError):
                success = self.write_summary_html(url, 'tmp.html')
                if success:
                    text = self.get_plain_text('tmp.html')
                    if min_length < len(text) < max_length:
                        f = open(output, 'w')
                        f.write(text.encode('utf-8'))
                        f.close()
                        return 0 # success
                    else:
                        return 1 # text too short or too long
                return 2 # cannot get summary
        except:
            return 2


    def write_summary_html(self, url, output):
        """
        Step 1: write summary of the web page to a tmp html
        TODO: get rid of the annoying error message
        """
        # print 'readability'
        try:
            html = urllib.urlopen(url).read()
            article = Document(html).summary()
            article = sub_ms_chars(article)
            f = open(output, 'w')
            f.write(article.encode('utf-8'))
            f.close()
            return True
        except:
            return False

    def get_plain_text(self, url):
        """
        Step 2: get plain text from lynx
        timeout in 3 sec
        """
        # print 'lynx'
        data = ""
        cmd = "lynx -dump -nolist -notitle \"{0}\"".format(url)
        lynx = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        t = threading.Timer(3, kill_lynx, args=[lynx.pid])
        t.start()
        data = lynx.stdout.read()
        t.cancel()
        data = data.decode("utf-8", 'ignore')
        return clean_lynx(data)


##############################################
if __name__ == '__main__':
    crawler = Crawler()
    crawler.process('feeds.txt')
