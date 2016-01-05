from flask import Flask
from flask import render_template

import pika

app = Flask(__name__)

@app.route('/')
def main():
    return 'main'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=21000, debug=True) # only for debug
