'''
 serial.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/08/19
 Copyright 2019 Wess Cope
'''

import json
import asyncio

from tornado.ioloop     import IOLoop
from tornado.gen        import coroutine, sleep
from tornado.web        import Application, RequestHandler
from tornado.websocket  import WebSocketHandler
from tornado.queues     import Queue
from ..serial           import SerialConnection
from .resource          import SocketResource

class SerialResource(SocketResource):
  dispatch  = None
  buffer    = Queue()

  async def connect(self, port=None, baudrate=None, *args, **kwargs):
    if not port and not baudrate:
      self.write_error({'error':'Connect requires a port and baudrate'})
      return

    self._serial_connect(port, baudrate)

  async def command(self, code, *args, **kwargs):
    if not self.dispatch:
      self.write_error({'error':'Nothing connected.'})
      return

    print("Writing command: ", code)
    self.write_message({'cmd': f'Running code: {code}'})
    await self.dispatch.write(code)

  async def disconnect(self):
    if not self.dispatch:
      return

    print("Disconnecting")
    await self.dispatch.close()

  async def _process_buffer(self):
    async for msg in self.buffer:
      self.write_message({"response" : msg.decode("utf-8")})
      await sleep(0.01)

  async def _buffer_output(self, msg):
    await self.buffer.put(msg)

  def _serial_connect(self, port, baudrate):
    self.write_message({"status": "Connecting to port {} with baudrate {}".format(port, baudrate)})

    if self.dispatch == None:
      IOLoop.current().spawn_callback(self._process_buffer)
      self.buffer.join()

    self.dispatch = SerialConnection(port, baudrate)
    self.dispatch.run(reader=self._buffer_output)
