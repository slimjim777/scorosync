#!/usr/bin/env python
import os
from scoro2clearbooks import app as application


IP = os.environ.get('OPENSHIFT_PYTHON_IP', 'localhost')
PORT = int(os.environ.get('OPENSHIFT_PYTHON_PORT', 8080))


if __name__ == '__main__':
    application.run(IP, PORT)
