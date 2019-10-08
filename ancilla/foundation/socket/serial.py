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

  def connect(self, port=None, baudrate=None, *args, **kwargs):
    if not port and not baudrate:
      self.write_error({'error':'Connect requires a port and baudrate'})
      return

    self._serial_connect(port, baudrate)

  async def _process_buffer(self):
    async for msg in self.buffer:
      msg = msg.decode("utf-8")

      self.write_message(msg)
      await sleep(0.01)

  async def _buffer_output(self, msg):
    print("From Serial: ", msg)
    await self.buffer.put(msg)

  def _serial_connect(self, port, baudrate):
    self.write_message({"status": "Connecting to port {} with baudrate {}".format(port, baudrate)})

    if self.dispatch == None:
      IOLoop.current().spawn_callback(self._process_buffer)
      self.buffer.join()

    self.dispatch = SerialConnection(port, baudrate)
    self.dispatch.run(reader=self._buffer_output)
