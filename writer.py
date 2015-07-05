#!/usr/bin/python
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import sys
import os

# TODO 
# make sure time is right
# more metadata query support to get a subset of the texts
# write a flag in db to indicate the text is already written

def write(data_dir, db = 'crawler'):
    client = MongoClient()
    texts = client[db]['texts']
    count = 1

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    for entry in texts.find():
        f = open(os.path.join(data_dir, '%d.txt' % count), 'w')
        text = entry['text'].decode('utf-8', 'ignore').encode('utf-8', 'ignore')
        f.write(text)
        f.close()
        count += 1


if __name__ == '__main__':
    write(sys.argv[1])