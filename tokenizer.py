#!/usr/bin/python
# -*- coding: utf-8 -*-

from segtok.segmenter import split_multi
from segtok.tokenizer import word_tokenizer, split_contractions
from pymongo import MongoClient
import sys


def tokenize(output_file, db = 'crawler'):
    client = MongoClient()
    texts = client[db]['texts']
    f = open(output_file, 'w')
    # (TODO: some query to get specific data)
    for entry in texts.find():
        text = entry['text'].decode('utf-8', 'ignore')
        # (optional: write article level data)
        for sent in split_multi(text):
            for token in word_tokenizer(sent):
                f.write('%s\t%s\n' % (token.encode('utf-8', 'ignore'), 'X'))
            f.write('\n')
    f.close()

if __name__ == '__main__':
    tokenize(sys.argv[1])