# -*- encoding: utf-8 -*-

import datetime
import logging
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from logentries import LogentriesHandler

DEBUG = False

engine = create_engine('postgres://urrpegktasoewc:bzCIGXqXTgHJOFek8uwBTPrqlS@ec2-54-197-241-239.compute-1.amazonaws.com:5432/dbpll7ajleqep4')
Session = sessionmaker(bind=engine)
session = Session()

LOGENTRIES_KEY = os.environ['LOGENTRIES_KEY']

RABBITMQ_BIGWIG_RX_URL = os.environ['RABBITMQ_BIGWIG_RX_URL']
RABBITMQ_BIGWIG_TX_URL = os.environ['RABBITMQ_BIGWIG_TX_URL']

RABBITMQ_QUEUE = 'nixiko_jobqueue'

TWITTER_CONSUMER_KEY = os.environ['TWITTER_CONSUMER_KEY']
TWITTER_CONSUMER_SECRET = os.environ['TWITTER_CONSUMER_SECRET']
TWITTER_ACCESS_KEY = os.environ['TWITTER_ACCESS_KEY']
TWITTER_ACCESS_SECRET = os.environ['TWITTER_ACCESS_SECRET']

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'
log_level = logging.DEBUG if DEBUG else logging.INFO
logging.basicConfig(stream=sys.stdout, level=log_level, format=LOG_FORMAT)

log = logging.getLogger(__name__)
log.addHandler(LogentriesHandler(LOGENTRIES_KEY))


MAX_H = 600
NIXIKO_IMG = '/nixiko/img/nixiko.png'

DATE_OPERATION = datetime.date(2012, 8, 3)
runtime_literals = [u'%\(업타임\)', u'%\(생일\)', u'%\(랜덤100\)', u'%\(랜덤10\)', u'%\(팔로어_멘션\)', u'%\(팔로어_이름\)', u'%\(랜덤(\d+)[,](\d+)\)']
all_random_exceptions = [u'문장', u'감탄사', u'형용사', u'해시', u'블라인드', u'부사']


P_NIXIKO_COMPOSITION = 0.4
