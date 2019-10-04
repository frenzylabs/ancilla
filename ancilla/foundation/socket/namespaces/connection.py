'''
 connection.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''
import asyncio

from flask_socketio import (
  Namespace,
  send, 
  emit, 
  join_room, 
  leave_room
)

from ...serial      import SerialConnection

class ConnectionNamespace(Namespace):
  _connections = dict()

  def on_connect(self):
    print("Connection made")

  def on_disconnect(self):
    pass

  def on_open(self, data):
    print("data: ", data)

    _conn = SerialConnection(**data)
    _conn.start()

    self._connections[data['name']] = _conn
    join_room(data['name'])

