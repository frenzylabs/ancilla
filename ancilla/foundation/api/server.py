'''
 http_server.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import os

from flask            import Flask, Response, send_from_directory
from flask_restful    import Api
from flask_cors       import CORS
from ..env            import Env
from ..server         import Server
from ..socket.server  import WSServer

from .resources import (
  PrinterResource,
  PortsResource
)

UI_FOLDER = os.path.abspath("{}/../ui/dist".format(os.path.dirname(__file__)))

class APIServer(object):
  @property
  def app(self):
    _app = Flask("ancilla", static_folder=UI_FOLDER, static_url_path="/app")
    _app.config['SECRET_KEY'] = 'wanker'

    _app.add_url_rule('/', 'index', Server.Action(self.index))
    
    self.api = Api(_app)

    self.api.add_resource(PrinterResource, '/printers')
    self.api.add_resource(PortsResource,    '/ports')

    CORS(_app)
    return _app

  @property
  def ws(self):
    _ws = WSServer(self.app)

    return _ws

  @property
  def manager(self):
    return Manager(self.app)

  def index(self, *args, **kwargs):
    return self.app.send_static_file('index.html')

  def start(self):
    self.ws.run(host='0.0.0.0', port=5000, debug=(Env.get('RUN_ENV') == 'DEV'))

