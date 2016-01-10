# -*- encoding: utf-8 -*-

import random
import re

import tweepy
from sqlalchemy.orm.exc import NoResultFound

from script import Script
from config import *
from dbscheme import ActiveScript, Config, ConditionScript, Follower
from dbscheme import PeriodicScript, ResponseScript, WordScript


class NixConf:
    @classmethod
    def load_config(self):
        log.debug('load_config called')

        nix_conf = {}
        for config in session.query(Config):
            key = config.key.encode('utf-8')
            value = config.value.encode('utf-8')
            nix_conf[key] = value

        return nix_conf

    @classmethod
    def update_config(self, nix_conf):
        log.debug('update_config called')
        try:
            for key in nix_conf:
                conf = Config(key, nix_conf[key])
                session.merge(conf)
            session.commit()
        except:
            log.exception('failed to update config')


class NixUtil:
    @classmethod
    def get_twitter_auth(self):
        auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_KEY, TWITTER_ACCESS_SECRET)
        api = tweepy.API(auth)
        return api

    @classmethod
    def get_random_from_subtable(self, subtable):
        count = int(subtable.count())
        return subtable[int(count*random.random())]

class Nixiko:
    def __init__(self, debug=False):
        log.debug(' [ ] initializing Nixiko')

        self.api = NixUtil.get_twitter_auth()
        self.config = NixConf.load_config()
        self.special_literals = [
            [(u'!멘션 중지', u'!멘션 그만', u'!멘션 중단', u'!멘션 재개', u'!멘션 다시'), self.process_toggle_block_mention],
            [(u'내생일', u'!생일', u'내 생일', u'나의 생일'), self.process_birthday],
        ]
        self.debug = debug

        log.debug(' [v] initializing Nixiko finished')

    def tweet(self):
        periodic = NixUtil.get_random_from_subtable(session.query(PeriodicScript).filter_by(is_blind=0))
        script = Script(periodic.contents, periodic.image_keyword)
        return self.do_tweet(script)

    def mention(self, input_mentions=[]):
        assert(isinstance(input_mentions, list))

        log.debug('process_mention called')

        if self.config['auto_mention'] != 'true':
            log.info('nixiko auto mention is off')
            return

        scripts = []
        if not input_mentions:
            since_id = self.config['last_mention_id']
            received_mentions = self.api.mentions_timeline(since_id=since_id, count=5)
            # since_id 옵션으로 멘션들을 불러오므로, 처리한 마지막 트윗의 아이디를 기록
            if received_mentions:
                # tweepy에서 self.api.mentions를 호출할 경우 시간 역순으로 나오기 때문에, 시간 순으로 처리하기 위해선
                # 한번 뒤집어주는 것이 필요함.
                received_mentions.reverse()
        else:
            received_mentions = input_mentions

        log.debug(u'received_mention #: {}'.format(len(received_mentions)))
        for mention in received_mentions: # for each mentions
            minfo = self.fetch_mention_info(mention)

            log.info(u'받은 멘션: {} (from {})'.format(minfo['text'], minfo['screen_name']))
            # 셀프 멘션에 대한 재멘션을 방지. 셀프멘션은 무시한다.
            if minfo['screen_name'] == 'nixieko': continue

            minfo['text'] = minfo['text'].replace(self.config['bot_name'], '').strip()

            # follower 추가를 먼저 한다.
            self.process_follower(minfo)

            # screen_name 제거
            minfo['text'] = self.remove_screen_name(minfo['text'])

            # 특수기능 처리
            if self.process_special_mention(minfo): break

            # 학습 처리
            if ':' in minfo['text'] and len(minfo['text'].split(':'))>=2 and 'RT' not in minfo['text'] and 'http' not in minfo['text']:
                log.debug(u'학습멘션: {}'.format(minfo['text']))
                split_words = minfo['text'].split(':')
                new_category = split_words[0].strip()
                new_word = ' '.join(split_words[1:]).strip() # escape!

                if ',' in new_word: # multi learn
                    new_words = map(lambda x: x.strip(), new_word.split(','))
                    n_known_word = 0
                    for new_word in new_words:
                        existing_word = self.get_words(contents=new_word).first()
                        if existing_word:
                            n_known_word += 1
                            log.info(u'중복 단어: {} {} by {}'.format(new_category, new_word, minfo['screen_name']))
                        else: # 학습성공
                            log.info(u'학습 성공: {} {} by {}'.format(new_category, new_word, minfo['screen_name']))
                            self.process_learn(new_category, new_word, minfo['screen_name'])

                    if n_known_word == 0:
                        subtable = session.query(ConditionScript).filter_by(keyword='multilearn')
                        condition_script = NixUtil.get_random_from_subtable(subtable)
                        script = Script(condition_script.contents, condition_script.image_keyword)
                        script.replace(u'%{대표단어}', new_words[0])
                        script.replace(u'%{배운수}', str(len(new_words)))
                    elif n_known_word == len(new_words):
                        subtable = session.query(ConditionScript).filter_by(keyword='multilearn_allknown')
                        condition_script = NixUtil.get_random_from_subtable(subtable)
                        script = Script(condition_script.contents, condition_script.image_keyword)
                    else:
                        subtable = session.query(ConditionScript).filter_by(keyword='multilearn_partlyknown')
                        condition_script = NixUtil.get_random_from_subtable(subtable)
                        script = Script(condition_script.contents, condition_script.image_keyword)
                        script.replace(u'%{대표단어}', new_words[0])
                        script.replace(u'%{배운수}', str(len(new_words) - n_known_word))
                        script.replace(u'%{중복수}', str(n_known_word))

                    script.translate()
                    script.mention(minfo['screen_name'])
                    self.do_tweet(script, minfo['id'])
                    scripts += [script]
                    continue
                        

                log.debug('existing word')
                existing_word = self.get_words(contents=new_word).first()
                if existing_word:
                    log.info(u'이미 알고 있는 단어: {} in {}'.format(new_word, existing_word.keyword))

                    subtable = session.query(ConditionScript).filter_by(keyword='duplicate')
                    condition_script = NixUtil.get_random_from_subtable(subtable)
                    script = Script(condition_script.contents, condition_script.image_keyword)

                    script.replace_numbered_literals([minfo['name'], new_word, new_category])
                    script.translate()
                    script.mention(minfo['screen_name'])
                    self.do_tweet(script, minfo['id'])
                    scripts += [script]
                    break
                else: # 학습 성공
                    log.info(u'학습 성공: {} {} by {}'.format(new_category, new_word, minfo['screen_name']))
                    subtable = session.query(ConditionScript).filter_by(keyword='learn')
                    condition_script = NixUtil.get_random_from_subtable(subtable)
                    script = Script(condition_script.contents, condition_script.image_keyword)
                    script.replace_numbered_literals([minfo['name'], new_word, new_category]);
                    script.translate()
                    scripts += [script.mention(minfo['screen_name'])]
                    self.process_learn(new_category, new_word, minfo['screen_name'])
                continue

            # 키워드 찾기
            log.debug('finding keyword...')
            script_candidate = []
            numbered_literals = []
            keywords_found = []
            max_match = 0
            keyword_literal = session.query(ResponseScript).filter_by(is_blind=0)
            for response in filter(lambda x:not x.keyword.startswith('%'), keyword_literal):
                keywords = response.keyword
                for keyword in keywords.split(','):
                    partial_keywords = map(unicode.strip, keyword.split('&&'))
                    for partial_keyword in partial_keywords:
                        if minfo['text'].find(partial_keyword.strip()) < 0: # if not found
                            break
                    else: # all match!
                        keywords_found.append(partial_keyword)
                        if max_match > len(partial_keywords):
                            continue
                        elif max_match < len(partial_keywords):
                            script_candidate = []
                            max_match = len(partial_keywords)
                        try:
                            script = Script(response.contents, response.image_keyword)
                        except:
                            log.exception(u'category error: '.format(contents))
                        script.replace(u'%{상대}', minfo['name'])
                        script.replace(u'%{키워드}', keyword.strip())
                        script_candidate.append(script)
            if script_candidate: # if there was a match(es)
                for keyword in keywords_found:
                    log.debug(u'{} keyword found: {}'.format(len(keywords_found), keyword))
                script = random.choice(script_candidate)
                script.translate()
                script.mention(minfo['screen_name'])
                self.do_tweet(script, minfo['id'])
                scripts += [script]
                continue
            log.debug('keyword not found')

            # 카테고리 찾기
            log.debug('finding category...')
            script_candidate = []
            keywords_found = []
            for keyword in self.get_words(is_blind=0):
                if keyword.contents in minfo['text']:
                    keywords_found.append(keyword.contents)
                    # category found
                    script = ''
                    category = keyword.keyword
                    try:
                        subtable = session.query(ResponseScript)\
                                    .filter_by(is_blind=0)\
                                    .filter(ResponseScript.keyword.like('\%('+ category +')'))
                        response_script = NixUtil.get_random_from_subtable(subtable)
                        script = Script(response_script.contents, response_script.image_keyword)
                    except:
                        log.exception(u'Script category error: '.format(category))
                        continue
                    try:
                        if not script: continue
                        script.replace(u'%{상대}', minfo['name'])
                        script.replace(u'%{키워드}', keyword.contents)
                        script_candidate += [script]
                    except:
                        log.exception(u'Error: category: {}, opponent: {}, keyword: {}, script: {}' \
                                .format(category, minfo['name'], keyword.contents.strip(), script))
                        raise

            if script_candidate:
                for keyword in keywords_found:
                    log.debug(u'{} keyword found: {}'.format(len(keywords_found), keyword))
                script = random.choice(script_candidate)
                script.translate()
                scripts += [script.mention(minfo['screen_name'])]
                continue

            # 해당사항 없음
            log.debug('받은 멘션이 어떤 카테고리에도 들어가지 않습니다. 랜덤한 스크립트를 선택합니다.')
            subtable = session.query(ConditionScript).filter_by(is_blind=0).filter_by(keyword='unknown')
            condition_script = NixUtil.get_random_from_subtable(subtable)
            script = Script(condition_script.contents, condition_script.image_keyword)
            script.replace(u'%{상대}', minfo['name'])
            script.translate()
            script.mention(minfo['screen_name'])
            self.do_tweet(script)
            scripts += [script]

        if not input_mentions: # only if processed w/ timeline
            if received_mentions:
                try:
                    log.debug(u'now update received mention id: {}'.format(str(received_mentions[-1].id)))
                    self.config['last_mention_id'] = str(received_mentions[-1].id)
                    if not DEBUG: NixConf.update_config(self.config)
                except:
                    log.exception('id fetching failed')

        return scripts

    def active(self):
        log.debug('process_active_mention called')
        if self.config['active_mention'] == 'false':
            log.info('nixiko active mention off')
            return

        active_subtable = session.query(ActiveScript).filter_by(is_blind=0)
        active = NixUtil.get_random_from_subtable(active_subtable)
        script = Script(active.contents, active.image_keyword)
        followers = session.query(Follower).filter_by(is_blocked=0)
        while True:
            target_candidate = NixUtil.get_random_from_subtable(followers)
            try:
                target = self.api.get_user(target_candidate.mention_id)
                break
            except tweepy.error.TweepError:
                log.error(u'user not exist: {}({})'.format(target_candidate.screen_name, target_candidate.mention_id))

        script.replace(u'%{이름}', target.name)
        script.replace(u'%{아이디}', target.screen_name)
        script.translate()

        mention_id = target.screen_name
        log.info(u'active mention to {}: {}'.format(mention_id, script.script))

        self.do_tweet(script)
        return

    def get_words(self, keyword=None, contents=None, is_blind=None):
        words = session.query(WordScript)
        if contents: words = words.filter_by(contents=contents)
        if is_blind != None: words = words.filter_by(is_blind=is_blind)
        return words

    def process_follower(self, minfo):
        log.debug('process_follower called')
        mention_user = session.query(Follower).filter_by(uniqueid=minfo['id'])
        try:
            user = mention_user.first()
        except NoResultFound:
            mention_user = session.query(Follower).filter_by(mention_id = minfo['screen_name'])

        try:
            mention_user = mention_user.one()
            mention_user.closeness += 1
            mention_user.uniqueid = minfo['id']
            mention_user.screen_name = minfo['name']
            log.debug(u'팔로어: {}, 호감도+1'.format(mention_user.screen_name))
        except NoResultFound:
            mention_user = Follower(minfo['name'], minfo['screen_name'])
            log.debug(u'팔로어 adding: {}({})'.format(minfo['name'], minfo['screen_name']))
        except MultipleResultsFound:
            log.error(u'중복유저: {}({})'.format(minfo['name'], minfo['screen_name']))
        mention_user.modified_at = datetime.datetime.now()
        try:
            session.add(mention_user)
            session.commit()
        except:
            log.exception(u'팔로어 학습 실패: {}'.format(repr(mention_user)))
            raise

    def process_learn(self, category, word, name):
        log.debug('process_learn called')
        new_word = WordScript(category, word, name)
        if not DEBUG:
            try:
                session.add(new_word)
            except:
                log.exception(u'학습 실패: {}'.format(word))
                raise
            log.info(u'학습 성공: {}'.format(new_word.contents))
        session.commit()
        log.debug('process_learn done')

    def fetch_mention_info(self, mention):
        log.debug('fetch_mention_info called')
        minfo = {}
        if type(mention) == unicode:
            minfo['screen_name'] = u'kimkkiruk'
            minfo['name'] = u'김끼룩'
            minfo['text'] = mention
            minfo['id'] = u'2'
        else:
            minfo['screen_name'] = mention.author.screen_name
            minfo['name'] = mention.author.name
            minfo['text'] = mention.text
            minfo['id'] = mention.id_str
        return minfo

    def process_birthday(self, minfo, keyword):
        log.debug('insert_birthday called')
        
        user = session.query(Follower).filter_by(uniqueid = minfo['id']).one()

        SCRIPT_UNKNOWN = [
                u'%(감탄사) 생일이 언제라는건지 잘 모르겠다요.. 대충 %(랜덤1,12)월 %(랜덤1,28)일로 해두면 되는거냐요?',
                u'생일이 그러니까 언제라는 거냐요! 모른다 닉시코는! %(해시)',
                u'닉시코는 모르겠다요.. %(사람)(이)랑 같은 생일...이다요?']
        SCRIPT_INPUTOK = [
                u'알았다요! %d월 %d일이라는거다요?',
                u'알았다요! 기억해두겠다요! %d월 %d일이다요?']
        SCRIPT_MODIFYOK = [
                u'에엣 %d월 %d일인줄 알았는데.. 알겠다요 %d월 %d일! %s의 생일!',
                u'알겠다요 %d월 %d일이 아니라 %d월 %d일... %s의 생일은 그렇게 기억해두면 되는거다요?']
        SCRIPT_DELETEOK = [
                u'알았다요. 닉시코는 이제 %s의 생일 같은거 모른다요?',
                u'알았다요. 닉시코는 기억에서 %s의 생일 지.웠.다.요.']
        SCRIPT_DUPLICATE = [
                u'알고 있다요! 생일이 그 날이라는거! 이미 알려줬잖다요? 잊지 않는다요!',
                u'에에 이미 알고 있다요? 닉시코를 무시하면 무참하게 당하게 될거다요!']

        KEYWORD_FORGET = ['잊어', '지워', '삭제']
        
        mention = minfo['text'].encode('utf8') if type(minfo['text']) == unicode else minfo['text']
        mention_back = '@%s ' % minfo['screen_name']

        for keyword in KEYWORD_FORGET:
            if keyword in mention:
                user.birthday = None
                script = Script(random.choice(SCRIPT_DELETEOK) % minfo['name'])
                script.translate()
                script.mention(minfo['screen_name'])
                self.do_tweet(script, minfo['id'])
                break
        else:

            regex_bday = '(?P<month>\d{1,2})월.*?(?P<day>\d{1,2})일'
            bday = re.search(regex_bday, mention)

            if not bday:
                script = Script(random.choice(SCRIPT_UNKNOWN))
                script.translate()
                script.mention(minfo['screen_name'])
                self.do_tweet(script, minfo['id'])
                return
            b_month = int(bday.group('month'))
            b_day = int(bday.group('day'))

            try:
                birthday_in = datetime.datetime(2000, b_month, b_day)
            except ValueError:
                script = Script(random.choice(SCRIPT_UNKNOWN))
                script.translate()
                script.mention(minfo['screen_name'])
                self.do_tweet(script, minfo['id'])
                return

            if user.birthday is not None:
                if user.birthday.day == b_day and user.birthday.month == b_month:
                    script = Script(random.choice(SCRIPT_DUPLICATE))
                    script.translate()
                    script.mention(minfo['screen_name'])
                    self.do_tweet(script, minfo['id'])
                else:
                    script = Script(random.choice(SCRIPT_MODIFYOK) %
                        (user.birthday.month, user.birthday.day, b_month, b_day, minfo['name']))
                    script.mention(minfo['screen_name'])
                    self.do_tweet(script, minfo['id'])

            else:
                script = Script(random.choice(SCRIPT_INPUTOK) % (b_month, b_day))
                script.mention(minfo['screen_name'])
                self.do_tweet(script, minfo['id'])
            user.birthday = birthday_in

        session.add(user)
        session.commit()
        return

    def process_toggle_block_mention(self, minfo, keyword):
        log.debug(u'process_toggle_block_mention called with keyword: {}'.format(keyword.encode('utf8')))
        user = session.query(Follower).filter_by(uniqueid = minfo['id'])

        try: user = user.one()
        except NoResultFound: user = session.query(Follower).filter_by(mention_id = minfo['screen_name'])
        try: user = user.one()
        except: user = Follower(minfo['screen_name'], minfo['name'])

        SCRIPT_STOP = u'알았다요. 이제 먼저 말 걸지 않겠다요.. '
        SCRIPT_RESUME = u'헤헤 알았다요! 이제 닉시코가 먼저 말을 걸 수도 있다요!'

        if keyword.split()[1] in (u'중지', u'그만', u'중단'): # if suspend
            user.is_blocked = 1
            log.info(u'사용자 블록 전환: '.format(minfo['screen_name']))
            script = Script(SCRIPT_STOP)
            script.mention(minfo['screen_name'])
            self.do_tweet(script, minfo['id'])
        else: # if resume
            user.is_blocked = 0
            log.info(u'사용자 블록 해제: '.format(minfo['screen_name']))
            script = Script(SCRIPT_RESUME)
            script.mention(minfo['screen_name'])
            self.do_tweet(script, minfo['id'])

        session.add(user)
        session.commit()
        log.debug('toggle_block_mention done')

    def birthday(self):
        now = datetime.datetime.now()
        today = datetime.datetime(2000, now.month, now.day)
        bday_users = session.query(Follower).filter_by(birthday=today)
        subtable = session.query(ConditionScript).filter_by(is_blind=0).filter_by(keyword='bday')
        for bday_user in bday_users:
            script = Script(NixUtil.get_random_from_subtable(subtable).contents)
            script.replace(u'%{아이디}', bday_user.mention_id)
            script.replace(u'%{이름}', bday_user.screen_name)
            script.translate()
            self.do_tweet(script)
        return

    def do_tweet(self, script, in_reply_to=None, image_filename=None):
        assert(isinstance(script, Script))
        log.debug(u' [?] Tweet: {}'.format(script))

        if not script.translated: script.translate()

        if (self.debug):
            log.info(u' [!] Tweet: {}'.format(script))
            if in_reply_to:
                log.info(u' [!] in reply to: {}'.format(in_reply_to))
            if image_filename:
                log.info(u' [!] with a file: {}'.format(image_filename))
            return
        self.api.update_status(status=script.script, in_reply_to_status_id=in_reply_to)
        return

    def remove_screen_name(self, mention):
        log.debug('remove_screen_name called')
        mentioned = []
        regex_screen_names = re.compile('\@[^ ]+')
        regex_web_address = re.compile('http[^ ]+')
        regex_emoticon = re.compile(':[ ]*?3')
        regex_filtering = [regex_screen_names, regex_web_address, regex_emoticon]
        for custom_filter in regex_filtering:
            for to_remove in custom_filter.findall(mention):
                mention = mention.replace(' '+to_remove, '')
                mention = mention.replace(to_remove+' ', '')
                mentioned += [to_remove]
        return mention

    def process_special_mention(self, minfo):
        log.debug('process_special_mention called')
        for specials in self.special_literals:
            if isinstance(specials[0], str) or isinstance(specials[0], unicode):
                if specials[0] in minfo['text']:
                    specials[1](minfo, specials[0])
                    log.debug(u'special mention found: {}'.format(minfo['text']))
                    return True
            elif isinstance(specials[0], list) or isinstance(specials[0], tuple):
                for spkey in specials[0]:
                    if spkey in minfo['text']:
                        log.debug('special mention found: %s' % minfo['text'])
                        specials[1](minfo, spkey)
                        return True
        return False
