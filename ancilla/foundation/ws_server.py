'''
 ws_server.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/03/19
 Copyright 2019 Wess Cope
'''

from flask_socketio import SocketIO, send, emit

class WSServer(object):
  class Action(object):
    def __init__(self, handler):
      self.handler  = handler

    def __call__(self, *args):
      return self.handler(*args)

  def __init__(self, app, *args, **kwargs):
    self.app    = app
    self.socket = SocketIO(self.app)

  def echo(self, data):
    print("Data: ", data)
    emit('message', data)

  def run(self, host, port, debug, **kwargs):
    self.socket.init_app(self.app, cors_allowed_origins="*")
    self.socket.on_event('message', WSServer.Action(self.echo))
    self.socket.run(self.app, host=host, port=port, debug=debug,)
