#!/usr/bin/env python
import os
import sys
import logging

from flask import Flask
from scoro2clearbooks.utils import run_sync


app = Flask(__name__)


IP = os.environ.get('OPENSHIFT_PYTHON_IP', 'localhost')
PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT', 8080))


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'


@app.route('/sync')
def run():
    """
    Run a sync of the Scoro to ClearBooks process
    """
    run_sync()
    return 'Complete'


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500


if __name__ == '__main__':
    app.run(IP, PORT)
