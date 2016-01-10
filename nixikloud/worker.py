# -*- encoding: utf-8 -*-

import json
import time

import pika

from config import *

from nixiko import Nixiko

nixiko = Nixiko(debug=False)

def on_message(ch, method, properties, body):
    message = json.loads(body.decode('utf-8'))
    log.info(" [ ] Received request: %r" % message)

    action = message['action']
    args = message['args']

    if action == 'tweet':
        nixiko.tweet() # ignore repeat
    elif action == 'mention':
        if 'script' in args:
            nixiko.mention([args['script']])
        else:
            nixiko.mention()
    elif action == 'birthday':
        nixiko.birthday()
    elif action == 'active':
        nixiko.active()

    log.info(" [v] Finished request: %r" % message)
    ch.basic_ack(delivery_tag = method.delivery_tag)

    return 'on_message finished'


def consume():
    connection = \
        pika.BlockingConnection(pika.URLParameters(RABBITMQ_BIGWIG_RX_URL))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)

    channel.basic_consume(on_message, queue=RABBITMQ_QUEUE)
    log.info(' [*] Waiting for messages. To exit press CTRL+C')

    channel.start_consuming()

    return 'consume finished'

if __name__ == '__main__':
    consume()
