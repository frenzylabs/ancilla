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
  PortsResource
)

# Sockets
from ..socket import (
  SerialResource
)

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui/dist')

class APIServer(object):
  @property
  def app(self):
    settings = {
      'debug' : Env.get('RUN_ENV') == 'DEV',
      'static_path' : STATIC_FOLDER
    }

    _app = Application([
      (r"/printers", PrinterResource),
      (r"/ports", PortsResource),
      (r"/serial", SerialResource),
      (r"/app/(.*)", StaticFileHandler, {'path' : STATIC_FOLDER}),
    ], **settings)

    return _app

  def start(self):
    print("Starting api server...")
    self.app.listen(5000)
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()



# from flask            import Flask, Response, send_from_directory
# from flask_restful    import Api
# from flask_cors       import CORS

# from ..server         import Server
# from ..socket.server  import WSServer

# from .resources import (
#   PrinterResource,
#   PortsResource
# )

# UI_FOLDER = os.path.abspath("{}/../ui/dist".format(os.path.dirname(__file__)))

# class APIServer(object):
#   @property
#   def app(self):
#     _app = Flask("ancilla", static_folder=UI_FOLDER, static_url_path="/app")
#     _app.config['SECRET_KEY'] = 'wanker'

#     _app.add_url_rule('/', 'index', Server.Action(self.index))
    
#     self.api = Api(_app)

#     self.api.add_resource(PrinterResource, '/printers')
#     self.api.add_resource(PortsResource,    '/ports')

#     CORS(_app)
#     return _app

#   @property
#   def ws(self):
#     _ws = WSServer(self.app)

#     return _ws

#   @property
#   def manager(self):
#     return Manager(self.app)

#   def index(self, *args, **kwargs):
#     return self.app.send_static_file('index.html')

#   def start(self):
#     self.ws.run(host='0.0.0.0', port=5000, debug=(Env.get('RUN_ENV') == 'DEV'))

