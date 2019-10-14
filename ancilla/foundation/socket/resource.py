'''
 router.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/08/19
 Copyright 2019 Wess Cope
'''

import functools
import json

from tornado.websocket import WebSocketHandler

class SocketResource(WebSocketHandler):
  clients = set()

  def check_origin(self, origin):
    return True

  def open(self):
    print("Opening websocket connection")

    self.clients.add(self)
    self.write_message({'connection':'success'})

  def on_close(self):
    self.clients.remove(self)    

  async def on_message(self, message):
    try:
      msg     = json.loads(message)
      action  = msg.get('action')
      params  = {k:v for k,v in filter(lambda t: t[0] != "action", msg.items())}

      if not action:
        self.write_error({'error': 'no action provided'})
        return

      method = getattr(self, action)

      if not method:
        self.write_error({'error': f'no action {action} found'})
        return

      if len(params) > 0:
        await method(**params)
      else:
        await method()

    except json.JSONDecodeError as err:
      self.write_error({'error':"{}".format(err)})

  def stop(self, *args, **kwargs):
    for client in self.clients:
      client.close()

    self.close()
