'''
 server.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''
import socket

class Server:
  class Action(object):
    def __init__(self, handler):
      self.handler  = handler

    def __call__(self, *args):
      return self.handler(*args)
  
  @staticmethod
  def available_ports():
    for port in range(5000, 8000):
      with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        if 0 == sock.connect_ex(('127.0.0.1', port)):
          return port

