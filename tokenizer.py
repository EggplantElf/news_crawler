#!/usr/bin/python
# -*- coding: utf-8 -*-

from segtok.segmenter import split_multi
from segtok.tokenizer import word_tokenizer, split_contractions
from pymongo import MongoClient
import sys
import re


def tokenize(output_file):
    client = MongoClient()
    texts = client['crawler']['texts']
    f = open(output_file, 'w')
    # (TODO: some query to get specific data)
    for entry in texts.find():
        text = entry['text'].decode('utf-8', 'ignore')
        # (optional: write article level data)
        for sent in split_multi(text):
            for token in word_tokenizer(sent):
                if re.search("'s$", token):
                    f.write('%s\t%s\n' % (token[:-2].encode('utf-8', 'ignore'), 'X'))
                    f.write('%s\t%s\n' % (token[-2:].encode('utf-8', 'ignore'), 'X'))
                else:
                    f.write('%s\t%s\n' % (token.encode('utf-8', 'ignore'), 'X'))
                    
            f.write('\n')
    f.close()

def tokenize_on_date(output_file, date = '2015-07-05'):
    client = MongoClient()
    texts = client['crawler']['texts']
    f = open(output_file, 'w')
    # (TODO: some query to get specific data)
    for entry in texts.find({'date': date}):
        text = entry['text'].decode('utf-8', 'ignore')
        # (optional: write article level data)
        for sent in split_multi(text):
            for token in word_tokenizer(sent):
                if re.search("'s$", token):
                    f.write('%s\t%s\n' % (token[:-2].encode('utf-8', 'ignore'), 'X'))
                    f.write('%s\t%s\n' % (token[-2:].encode('utf-8', 'ignore'), 'X'))
                else:
                    f.write('%s\t%s\n' % (token.encode('utf-8', 'ignore'), 'X'))
                    
            f.write('\n')
    f.close()


if __name__ == '__main__':
    if len(sys.argv) == 2:
        tokenize(sys.argv[1])
    else:
        tokenize_on_date(sys.argv[1], sys.argv[2])