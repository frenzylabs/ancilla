'''
 http_server.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import os

from tornado.ioloop import IOLoop
from tornado.web    import Application, RequestHandler, StaticFileHandler


# Local imports
from ..env import Env

# Resources
from .resources import (
  PrinterResource,
  PortsResource,
  DocumentResource
)

# Sockets
from ..socket import (
  SerialResource
)

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui/dist')

class APIServer(object):
  def __init__(self, document_store):
    self.document_store = document_store

  @property
  def app(self):
    settings = {
      'debug' : Env.get('RUN_ENV') == 'DEV',
      'static_path' : STATIC_FOLDER
    }

    _app = Application([
      (r"/document",  DocumentResource, dict(document=self.document_store)),
      (r"/printers",  PrinterResource),
      (r"/ports",     PortsResource),
      (r"/serial",    SerialResource),
      (r"/app/(.*)",  StaticFileHandler, dict(path = STATIC_FOLDER)),
    ], **settings)

    return _app

  def start(self):
    print("Starting api server...")
    self.app.listen(5000)
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()
