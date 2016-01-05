import json

from flask import Flask
from flask import render_template
import pika

from config import *


app = Flask(__name__)

@app.route('/')
def main():
    return 'main'


@app.route('/run/<action>/<int:repeat>')
@app.route('/run/<action>/<args>')
def run(action='test', args='', repeat=1):
    log.info('action: {}, args: {}, repeat: {}'.format(action, args, repeat))

    message = {'action': action, 'args': args, 'repeat': repeat}
    return enqueue(message)

def enqueue(message):
    with pika.BlockingConnection(pika.URLParameters(RABBITMQ_BIGWIG_TX_URL)) as connection:
        channel = connection.channel()
        channel.queue_declare(queue=RABBITMQ_QUEUE)
        channel.basic_publish(
                exchange='', routing_key=RABBITMQ_QUEUE, body=json.dumps(message))
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=21000, debug=True) # only for debug
