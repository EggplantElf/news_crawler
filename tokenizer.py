#!/usr/bin/python
# -*- coding: utf-8 -*-

from segtok.segmenter import split_single, split_multi
from segtok.tokenizer import symbol_tokenizer, word_tokenizer, web_tokenizer
from segtok.tokenizer import split_possessive_markers, split_contractions
import sys
import os

# TODOS
# walk dir


def walk(input_dir, output_file):
    f = open(output_file, 'w')
    for input_file in os.listdir(input_dir):
        for sent in tokenize(os.path.join(input_dir, input_file)):
            if sent:
                for token in sent:
                    if token:
                        f.write('%s\t%s\n' % (token.encode('utf-8'), 'X'))
                f.write('\n')

    f.close()


def tokenize(input_file):
    text = open(input_file).read().decode('utf-8')
    sents = [split_contractions(word_tokenizer(sent)) for
            sent in split_multi(text)]
    # [[t1, t2, ...], [t1, t2, ...] ... ]
    return sents



if __name__ == '__main__':
    walk('data', 'data.iob')