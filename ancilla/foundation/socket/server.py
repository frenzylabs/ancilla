'''
 ws_server.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/03/19
 Copyright 2019 Wess Cope
'''

from flask_socketio import SocketIO, send, emit
from ..server       import Server

from .namespaces import (
  Connection
)

class WSServer(object):
  def __init__(self, app, *args, **kwargs):
    self.app    = app
    self.socket = SocketIO(self.app)
  def _setup(self):
    self.socket.init_app(self.app, cors_allowed_origins="*")

    conn = Connection('/connection')
    conn.websocket = self.socket

    self.socket.on_namespace(conn)

  def run(self, host, port, debug, **kwargs):
    self._setup()
    self.socket.run(self.app, host=host, port=port, debug=debug)
