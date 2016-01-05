# -*- encoding: utf8 -*-
import datetime
import json
import logging
import random
import re
import sys

import korean
import requests
import tweepy

from wand.image import Image

sys.path += ['/nixiko']
from config import *
#from gcustomsearch import GCustomSearch
from dbscheme import WordScript

with open(os.path.join(os.path.dirname(__file__), 'data.json')) as f:
    data = json.load(f)

# register more allomorphic particles
for forms in data['allomorphic_particles'].itervalues():
    particle = korean.Particle(*forms)
    for form in forms:
        korean.Particle.register(form, particle)

proofread = korean.l10n.proofread

def get_random_from_subtable(subtable):
    count = int(subtable.count())
    return subtable[int(count*random.random())]

class Script:

    def __init__(self, script, image_keyword=None):
        assert(isinstance(script, unicode))
        log.debug(u'script: {}, image_keyword: {}'.format(script, image_keyword))
        self.script = script
        self.image_keyword = image_keyword
        self.translated = False
        self.replacing_tuples = []
        self.numbered_literals = []

    def mention(self, reply_to, image_keyrowd=None):
        self.script = u'@{} {}'.format(reply_to, self.script)

    def translate(self):
        assert(not self.translated)

        self.script = self.do_translate(self.script, self.replacing_tuples)
        if self.image_keyword:
            log.debug(u'translating keyword: {} with {}'.format(self.image_keyword, self.numbered_literals))
            replacing_tuples = self.insert_numbered_literals(self.image_keyword, self.numbered_literals)
            self.image_keyword = self.do_translate(self.image_keyword, self.replacing_tuples + replacing_tuples)

        self.translated = True
        log.debug(u'translate done: {}'.format(self.script))
        return True

    def replace(self, literal, word, count=-1):
        num_appearance = self.script.count(literal)
        replacing_count = num_appearance if count == -1 else min(count, num_appearance)

        [self.replacing_tuples.append((literal, word)) for i in range(replacing_count)]
        log.debug(u'replace called: {} -> {} ({} times)'.format(literal, word, replacing_count))

    # (원단어, 목표 단어)의 튜플의 리스트를 인자로 받는다.
    #
    # 조사 처리를 위해 두 번의 치환이 이루어진다.
    # 1. 목표 단어의 읽을 수 있는 형태로 치환(1); to_be_replaced -> readable
    # 2. 조사 처리; proofread
    # 3. 원래 되어야 할 단어로 치환(2); readable -> to_replace
    def make_readable(self, script, replacing_tuples):
        assert(isinstance(script, unicode))
        log.debug(u'make_readable called: {}, {}'.format(script, replacing_tuples))
        replacing_tuples_readable = []
        for to_be_replaced, to_replace in replacing_tuples:
            readable = u''.join(c for c in to_replace if c.isalnum() or c.isspace() or korean.hangul.is_hangul(c))
            readable = korean.Loanword(readable, 'ita').read()
            readable = korean.Noun(readable).read()
            script = script.replace(to_be_replaced, readable, 1)

            log.debug(u'make readable: {} -> {} -> {}'.format(to_be_replaced, readable, to_replace))
            replacing_tuples_readable.append((readable, to_replace))

        script = korean.l10n.proofread(script)

        for readable, to_replace in replacing_tuples_readable:
            script = script.replace(readable, to_replace, 1)

        if replacing_tuples_readable:
            log.debug(u'calling do_translate with {}'.format(script))
            script = self.do_translate(script) # 이번에 치환한 경우 한번 더 반복

        return script

    def do_translate(self, script, replacing_tuples = None):
        assert(isinstance(script, unicode))

        log.debug(u'do_translate called: {} / {}'.format(script, replacing_tuples))
        if replacing_tuples is None: replacing_tuples = []

        script = self._process_runtime_literals(script)

        regex_literal = re.compile('%\([^\d%\|]+?\)')

        numbered_literals = []
        literals = regex_literal.findall(script)
        for literal in literals:
            category = literal[2:-1] # remove '%(' and ')'. could be better?
            all_categories = map(lambda x: x[0], session.query(WordScript.keyword).distinct())
            if category == u'랜덤':
                while True: # Las Vegas algorithm. maybe need to fix this.
                    subtable = session.query(WordScript).filter_by(is_blind=0)
                    random_word = get_random_from_subtable(subtable)
                    if random_word.keyword not in all_random_exceptions:
                        to_replace = random_word.contents
                        break
            elif category not in all_categories:
                log.error('카테고리 오류: {} for {}'.format(category, script))
                return
            else:
                subtable = session.query(WordScript).filter_by(is_blind=0).filter_by(keyword=category)
                to_replace = get_random_from_subtable(subtable).contents

            numbered_literals.append(to_replace)
            to_be_replaced = literal
            to_replace = self.do_translate(to_replace)
            replacing_tuples.append((to_be_replaced, to_replace))


        replacing_tuples += self.insert_numbered_literals(script, numbered_literals)
        replacing_tuples += self.process_selective_literals(script)
        script = self.make_readable(script, replacing_tuples)
        self.numbered_literals = numbered_literals
        log.debug(u'translate done: {}'.format(script))
        return script

    def _process_runtime_literals(self, script):
        log.debug(u'_process_runtime_literals called: {}'.format(script))

        def __calculate_birthday(dummy):
            dday = DATE_OPERATION - today
            while dday < datetime.timedelta(0):
                dday += datetime.timedelta(days=365)
            return dday.days

        def __calculate_general_random(numbers):
            start, end = numbers
            return random.randint(int(start), int(end))

        today = datetime.date.today()
        runtime_literal_processor = {
            u'%\(업타임\)': lambda x: (today-DATE_OPERATION).days,
            u'%\(생일\)': __calculate_birthday,
            u'%\(랜덤100\)': lambda x: random.randint(0, 100),
            u'%\(랜덤10\)': lambda x: random.randint(0, 9),
            u'%\(랜덤(\d+)[,](\d+)\)': __calculate_general_random,
        }
        for key in runtime_literal_processor:
            matched_literals = re.findall(key, script)
            for matched_literal in matched_literals:
                random.seed()
                to_be_replaced = unicode(matched_literal)
                to_replace = unicode(runtime_literal_processor[key](matched_literal))
                to_replace = self.do_translate(to_replace)
                script = re.sub(key, to_replace, script, 1)
                break
        return script

    def replace_numbered_literals(self, numbered_words):
        log.debug(u'replace_numbered_literals called: {}'.format(str(numbered_words)))
        for num in range(len(numbered_words)): # we don't begin with %(0)
            numbered_literal = '%(' + str(num) + ')'
            self.script = self.script.replace(numbered_literal, numbered_words[num])

    def insert_numbered_literals(self, script, numbered_words):
        log.debug(u'insert_numbered_literals called: {}'.format(str(numbered_words)))
        replacing_tuples = []
        for num in range(len(numbered_words)): # we don't begin with %(0)
            numbered_literal = '%(' + str(num + 1) + ')'
            num_appearance = script.count(numbered_literal)
            log.debug(u'{} num_appearance: {}'.format(numbered_literal, num_appearance))
            for i in range(num_appearance):
                replacing_tuples += [(numbered_literal, numbered_words[num])]
            if self.image_keyword:
                self.image_keyword.replace(numbered_literal, numbered_words[num])

        return replacing_tuples

    def process_selective_literals(self, script):
        log.debug(u'process_selective_literals called: {}'.format(script))
        regex_selective = re.compile('%\([^\d%]+?\|[^\d%]+?\)')
        literals = regex_selective.findall(script)

        replacing_tuples = []
        for literal in literals:
            words = literal[2:-1].split('|')
            to_be_replaced = literal
            to_replace = random.choice(words)
            to_replace = self.do_translate(to_replace)
            replacing_tuples.append((to_be_replaced, to_replace))
        return replacing_tuples

    def __str__(self):
        return u'<Script "{}", {}>'.format(self.script, self.translated)

if __name__ == '__main__':
    script = Script(u"hello world %(업타임), %(랜덤)(이)가 놀자고 함")
    script.replace('hello', 'hell')
    script.translate()
    script.do_tweet()
    print(script.script)
