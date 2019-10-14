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
  connections = {}

  async def connect(self, port=None, baudrate=None, *args, **kwargs):
    if not port and not baudrate:
      self.write_error({'error':'Connect requires a port and baudrate'})
      return
    print("Connect to serial: ")
    self._serial_connect(port, baudrate)

  async def command(self, code, *args, **kwargs):
    if not self.dispatch:
      self.write_error({'error':'Nothing connected.'})
      return

    print("Writing command: ", code)
    self.write_message({'cmd': f'Running code: {code}'})
    await self.dispatch.write(code)

  async def disconnect(self):
    print("Disconnect?")
    if not self.dispatch:
      return

    print("Disconnecting")
    await self.dispatch.close()

  def on_close(self):
    print("On Serial Close")
    super().on_close()
    if self.dispatch:
      self.dispatch.removeHandler(self._buffer_output)

  async def _process_buffer(self):
    print("PROCESS buffer ", self)
    print(SocketResource.clients)
    # for client in SocketResource.clients:
    #   print("HI CLIENT")
    #   client.write_message({"response" : "OK"})
    async for msg in self.buffer:
      if self.ws_connection:
        print("self = ", self)
        self.write_message({"response" : "OK"})
        await sleep(0.01)
      else:
        print("NO WEBSocKET CONN: ", self)
        print(SocketResource.clients)
        # return
      # client.write_message({"response" : msg.decode("utf-8")})
      

  async def _buffer_output(self, msg):
    print("buffer: ", msg)
    print(SocketResource.clients)
    print(self.dispatch.readers)
    print(self)
    await self.write_message({"response" : msg.decode("utf-8")})
    # await self.buffer.put(msg)

  @classmethod
  async def process_buffer(cls):
    for client in SocketResource.clients:
      print("HI CLIENT")
      # async for msg in client.buffer:
      #   self.write_message({"response" : "OK"})
      #   # client.write_message({"response" : msg.decode("utf-8")})
      #   await sleep(0.01)
      client.write_message({"response" : "OK"})
    
  def _serial_connect(self, port, baudrate):
    self.write_message({"status": "Connecting to port {} with baudrate {}".format(port, baudrate)})

    print("dispatch= ", self.dispatch)
    print("conns: ", SerialResource.connections)
    print("IOLOOP", IOLoop.current())
    
    
    if self.dispatch == None and SerialResource.connections.get(port):
        
        self.dispatch = SerialResource.connections[port]
        self.dispatch.addHandler(self._buffer_output)
    else:
      print("creating dispatch")
      self.dispatch = SerialConnection(port, baudrate)
      self.dispatch.run(reader=self._buffer_output)
      SerialResource.connections[port] = self.dispatch
    
    # IOLoop.current().add_callback(self._process_buffer)
    # self.buffer.join()    

    # if self.dispatch == None:
    #   IOLoop.current().add_callback(self._process_buffer)
    #   self.buffer.join()

    # print("creating dispatch")
    # self.dispatch = SerialConnection(port, baudrate)
    # self.dispatch.run(reader=self._buffer_output)
    # SerialResource.connections[port] = self.dispatch
