import datetime

from sqlalchemy import Column, Integer, String, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base

from config import *

Base = declarative_base()

class Config(Base):
    __tablename__ = 'config'
    key = Column(String(60), primary_key=True)
    value = Column(String(256))

    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return u"<Config>"

class Follower(Base):
    __tablename__ = 'followers'

    id = Column(Integer, primary_key=True)
    screen_name = Column(String(100))
    uniqueid = Column(String(100))
    mention_id = Column(String(100))
    added_at = Column(DateTime, default=datetime.datetime.now)
    modified_at = Column(DateTime, default=datetime.datetime.now)
    is_blocked = Column(Integer, default=0)
    closeness = Column(Integer, default=0)
    birthday = Column(Date)
    
    def __init__(self, screen_name, mention_id, uniqueid=None, added_at=None, modified_at=None):
        self.screen_name = screen_name
        self.uniqueid = uniqueid
        self.mention_id = mention_id
        self.added_at = added_at if added_at != None else datetime.datetime.now()
        self.modified_at = modified_at if modified_at != None else datetime.datetime.now()
        self.is_blocked = 0
        self.closeness = 1

    def __repr__(self):
        form = (self.screen_name,
                self.uniqueid,
                self.mention_id,
                self.added_at)
        return u"<Follower('%r', '%r', '%r', '%r')>" % form

    #@classmethod # XXX: maybe we don't need this. too expensive.
    #def gets(self, session):
        #return [instance for instance in session.query(Follower)]

class ActiveScript(Base):
    __tablename__ = 'script_active'

    id = Column(Integer, primary_key=True)
    contents = Column(String(512))
    added_by = Column(String(64), default='system')
    added_at = Column(DateTime, default=datetime.datetime.now)
    modified_by = Column(String(64), default='system')
    modified_at = Column(DateTime, default=datetime.datetime.now)
    is_blind = Column(Integer, default=0)
    image_keyword = Column(String(256), default=None)

    def __init__(self, contents, added_by):
        self.contents = contents
        self.added_by = added_by
        self.modified_by = added_by
        self.added_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()
        self.is_blind = 0
        self.image_keyword = image_keyword

    def __repr__(self):
        form = (self.contents, self.added_by, self.modified_by)
        return u"<ActiveScript('%r', '%r', '%r')>" % form

    @classmethod
    def gets(self, session):
        return [instance for instance in session.query(ActiveScript)]

class ConditionScript(Base):
    __tablename__ = 'script_condition'

    id = Column(Integer, primary_key=True)
    keyword = Column(String(512), index=True)
    contents = Column(String(512))
    added_by = Column(String(64), default='system')
    added_at = Column(DateTime, default=datetime.datetime.now)
    modified_by = Column(String(64), default='system')
    modified_at = Column(DateTime, default=datetime.datetime.now)
    is_blind = Column(Integer, default=0)
    image_keyword = Column(String(256), default=None)

    def __init__(self, keyword, contents, added_by, image_keyword=None):
        self.keyword = keyword
        self.contents = contents
        self.added_by = added_by
        self.modified_by = added_by
        self.added_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()
        self.is_blind = 0
        self.image_keyword = image_keyword

    def __repr__(self):
        form = (self.keyword, self.contents, self.added_by, self.modified_by)
        return u"<ConditionScript('%r', '%r', '%r', '%r')>" % form

    @classmethod
    def gets(self, session):
        return [instance for instance in session.query(ConditionScript)]

class PeriodicScript(Base):
    __tablename__ = 'script_periodic'

    id = Column(Integer, primary_key=True)
    contents = Column(String(512))
    added_by = Column(String(64), default='system')
    added_at = Column(DateTime, default=datetime.datetime.now)
    modified_by = Column(String(64), default='system')
    modified_at = Column(DateTime, default=datetime.datetime.now)
    is_blind = Column(Integer, default=0)
    image_keyword = Column(String(256), default=None)

    def __init__(self, contents, added_by, image_keyword=None):
        self.contents = contents
        self.added_by = added_by
        self.modified_by = added_by
        self.added_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()
        self.is_blind = 0
        self.image_keyword = image_keyword

    def __repr__(self):
        form = (self.contents, self.added_by, self.modified_by)
        return u"<PeriodicScript('%r', '%r', '%r')>" % form

    @classmethod
    def gets(self, session):
        return [instance for instance in session.query(PeriodicScript)]

class ResponseScript(Base):
    __tablename__ = 'script_response'

    id = Column(Integer, primary_key=True)
    keyword = Column(String(512), index=True)
    contents = Column(String(512))
    added_by = Column(String(64))
    added_at = Column(DateTime)
    modified_by = Column(String(64))
    modified_at = Column(DateTime)
    is_blind = Column(Integer)
    image_keyword = Column(String(256), default=None)

    def __init__(self, keyword, contents, added_by, image_keyword=None):
        self.keyword = keyword
        self.contents = contents
        self.added_by = added_by
        self.modified_by = added_by
        self.added_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()
        self.is_blind = 0
        self.image_keyword = image_keyword

    def __repr__(self):
        form = (self.keyword, self.contents, self.added_by, self.modified_by)
        return u"<ResponseScript('%r', '%r', '%r', '%r')>" % form

    @classmethod
    def gets(self, session):
        return [instance for instance in session.query(ResponseScript)]

class WordScript(Base):
    __tablename__ = 'script_word'

    id = Column(Integer, primary_key=True)
    keyword = Column(String(512), index=True)
    contents = Column(String(512))
    added_by = Column(String(64))
    added_at = Column(DateTime)
    modified_by = Column(String(64))
    modified_at = Column(DateTime)
    is_blind = Column(Integer)

    def __init__(self, keyword, contents, added_by):
        self.keyword = keyword
        self.contents = contents
        self.added_by = added_by
        self.modified_by = added_by
        self.added_at = datetime.datetime.now()
        self.modified_at = datetime.datetime.now()
        self.is_blind = 0

    def __repr__(self):
        form = (self.keyword, self.contents, self.added_by, self.modified_by)
        return u"<WordScript('%r', '%r', '%r', '%r')>" % form

    @classmethod
    def gets(self, session):
        return [instance for instance in session.query(WordScript)]
