'''
 serial_connection.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import traceback
import asyncio
import serial_asyncio

from concurrent   import futures
from serial.tools import list_ports


class SerialConnection(object):

  def __init__(self, port, baudrate, *args, **kwargs):
    self.port     = port.decode('utf-8')
    self.baudrate = baudrate
    print("Port = ", self.port)
    print("baudrate = ", self.baudrate)
    self.tasks    = []

  def run(self, reader=None):
    self.readerCallback = reader
    self.loop           = asyncio.get_event_loop()

    self.loop.create_task(self.open())

  def stop(self):
    self.loop.close()

  def write(self, msg):
    self.writer.write((msg + '\n').encode())

  async def open(self):
    print(f'Opening connection to {self.port}...')

    try:
      self.reader, self.writer = await serial_asyncio.open_serial_connection(url=self.port, baudrate=self.baudrate)
      
      self.tasks.append(
        asyncio.ensure_future(self._read())
      )
    except Exception:
      print(traceback.format_exc())

    print(f'Connected to {self.port}.')

  async def close(self):
    print(f'Closing connection to {self.port}...')

    for task in self.tasks:
      task.cancel()

      await asyncio.gather(task)


  async def _read(self):
    try:
      while True:
        msg = await self.reader.readuntil(b'\n')
        print("MESSAGE = ", msg)

        if self.readerCallback:
          await self.readerCallback(msg)

    except futures._base.CancelledError:
      print("Cancelled")
    except asyncio.streams.IncompleteReadError:
      print(traceback.format_exc())
    except Exception:
      print(traceback.format_exc())

## Statics
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

