'''
 serial_connection.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import asyncio
import serial_asyncio

from serial.tools import list_ports
from concurrent import futures

class SerialConnection(object):
  
  def __init__(self, port, baudrate, *args, **kwargs):
    self.port     = port
    self.baudrate = baudrate
    self.tasks    = []

  @staticmethod
  def baud_rates():
    return [
      2_000_000,
      1_500_000,
      1_382_400,
      1_000_000,
      921_600,
      500_000,
      460_800,
      256_000,
      250_000,
      230_400,
      128_000,
      115_200,
      111_112,
      76_800,
      57_000,
      56_000,
      38_400,
      28_800,
      19_200,
      14_400,
      9600 
    ]

  @staticmethod
  def list_ports():
    return [port.device for port in list_ports.comports()]

  def start(self, reader=None):
    self.readerCallback = reader
    self.loop           = asyncio.get_event_loop()

    self.loop.create_task(self.open())

  def stop(self):
    self.loop.close()

  async def write(self, msg):
    self.writer.write(msg)

  async def open(self):
    print(f'Opening connection to {self.port}...')

    try:
      self.reader, self.writer = await serial_asyncio.open_serial_connection(url=self.port, baudrate=self.baudrate)
      
      task = asyncio.ensure_future(self._read_handler())
      self.tasks.append(task)

    except Exception:
      print(traceback.format_exc())

    print(f'Connection to {self.port} is open.')

  async def close(self):
    print(f'Closing connection to {self.port}')

    for task in self.tasks:
      task.cancel()
      await asyncio.gather(task)

    print(f'Closed connection to {self.port}')

  async def _process_buffer(self):
    async for msg in self.buffer:
      msg = msg.decode("utf-8")
      
      self.write(msg)
      await sleep(0.01)

  async def _buffer_output(self, msg):
    print(msg)

  async def _read_handler(self):
    print("Read Handler")

    try:
      while True:
        msg = await self.reader.readuntil(b'\n')

        if self.readerCallback:
          await self.readerCallback(msg)
        else:
          await self._buffer_output(msg)

    except futures._base.CancelledError:
      print("Cancelled")
    except asyncio.streams.IncompleteReadError:
      print(traceback.format_exc())
    except Exception:
      print(traceback.format_exc())
