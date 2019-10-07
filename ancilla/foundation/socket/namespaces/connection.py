'''
 connection.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''
import time
import threading

from queue import Queue

from flask_socketio import (
  Namespace,
  send, 
  emit, 
  join_room, 
  leave_room
)

from ...serial import SerialConnection

class ConnectionNamespace(Namespace):
  websocket = None

  _connections  = dict()
  _queue        = Queue()

  def on_connect(self):
    print("Connection made")

  def on_disconnect(self):
    print("Disconnect")
    pass

  def on_open(self, data):
    print("Opened")

    try:
      _conn             = SerialConnection(**data)
      _conn.websocket   = self.websocket
      _conn.on_message  = self.serial_incoming

      self._conn = _conn

      _conn.start()

      # _thread = threading.Thread(target=_conn.start)
      # _thread.start()

      # self._connections[data['name']] = _conn

      # print(threading.current_thread().__class__.__name__)
      print(threading.current_thread())
      print(threading.main_thread())
      print(self.websocket)
      self.websocket.emit('message', "Connected")
      # _conn
    except:
      self.emit('message', "Unable to connect to {}".format(data["name"]))
      


  def on_message(self, data):
    print("my on message")
    pass

  def serial_incoming(self, data):
    if len(data) > 0:
      print("Data: ", data)
      print(threading.current_thread())
      self.emit('message', data=data)
