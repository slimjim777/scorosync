import logging

from flask import Flask
from scoro2clearbooks.utils import run_sync


app = Flask(__name__)


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'


@app.route('/sync')
def run():
    """
    Run a sync of the Scoro to ClearBooks process
    """
    errors = run_sync()

    if len(errors) == 0:
        return "Complete"
    else:
        return "Complete with {} errors".format(len(errors))


@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return """
    An internal error occurred: <pre>{}</pre>
    See logs for full stacktrace.
    """.format(e), 500
