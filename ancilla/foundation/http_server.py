'''
 http_server.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import os

from flask          import Flask, Response, send_from_directory
from flask_restful  import Api
from flask_cors     import CORS
from .env import Env

from .api import (
  PrinterResource,
  PortsResource
)

UI_FOLDER = os.path.abspath("{}/../ui/dist".format(os.path.dirname(__file__)))

class HttpServer(object):
  class Action(object):
    def __init__(self, handler):
      self.handler  = handler

    def __call__(self, *args):
      return self.handler()


  def __init__(self, *args, **kwargs):
    self.app = Flask(
      "ancilla",
      static_folder=UI_FOLDER,
      static_url_path="/app"
    )

    self.api = Api(self.app)

  @property
  def manager(self):
    return Manager(self.app)

  def index(self, *args, **kwargs):
    return self.app.send_static_file('index.html')

  def start(self):
    self.app.add_url_rule('/', 'index', HttpServer.Action(self.index))
    self.api.add_resource(PrinterResource, '/printers')
    self.api.add_resource(PortsResource,    '/ports')

    CORS(self.app)

    if Env.get('RUN_ENV') == 'DEV':
      self.app.run(host='localhost', port=5000, debug=True)
    else:
      self.app.run(host='localhost', port=5000)
