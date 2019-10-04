'''
 serial_connection.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import serial
import time
import threading
import collections

from types        import SimpleNamespace
from serial.tools import list_ports

class SerialConnection(object):

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


  def __init__(self, port, baudrate, *args, **kwargs):
    self.port     = port
    self.baudrate = baudrate
    self.serial   = serial.Serial(self.port, self.baudrate, timeout=3)
    self.output   = collections.deque()

    # Handlers
    self._on_message  = None
    self._on_send     = None
    self._on_log      = None

    # Threading
    self.lock       = SimpleNamespace(**{'open': threading.Lock(), 'callback': threading.RLock()})
    self._thread    = None
    self._terminate = False
    self._alive     = False

  def start(self):
    self._thread = threading.Thread(target=self._run)
    self._thread.setDaemon(True)
    self._thread.start()


  def _run_alive(self):
    while True:
      if self._alive:
        break
      else:
        with self.lock.open:
          self._open()

      time.sleep(1)

  def _run(self):
    self._run_alive()

    while self._alive:
      time.sleep(0.1)
      self._read()

  def _open(self):
    if not self.serial.port and self.serial.baudrate:
      raise ValueError('Port and baudrate are required for a serial connection')

    try:
      if self.serial.isOpen():
        self._close()
      self.serial.open()
    except serial.SerialException as e:
      raise
    else:
      self._alive = True
      self._thread = threading.Thread(target=self._receive)
      self._thread.setDaemon(True)
      self._thread.start()

  def _close(self):
    try:
      self.serial.close()
      self._alive     = False
      self._terminate = False
    except:
      pass
    
  def _receive(self):
    while self._alive:
      time.sleep(0.1)
      self._read()


  def _read(self):
    while True:
      try:
        buffer = self.serial.readline().decode('utf-8')
        if not buffer:
          break

        print("Buffer: ", buffer)
        self._handle_buffer(buffer)
      except Exception as e:
        pass

  def _handle_buffer(self, buffer):
    pass

  @property
  def on_message(self):
    return self._on_message

  @on_message.setter
  def on_message(self, func):
    with self.lock.callback:
      self._on_message = func

  def send(self, msg):
    with self.lock.callback:
      if msg:
        if isinstance(msg, bytes):
          self.serial.write(msg)
        if isinstance(msg, str):
          self.serial.send(msg.encode('utf-8'))

#########
  # def start(self, reader=None):
  #   self.readerCallback = reader
  #   self.loop           = asyncio.get_event_loop()

  #   self.loop.create_task(self.open())

  # def stop(self):
  #   self.loop.close()

  # async def write(self, msg):
  #   self.writer.write(msg)

  # async def open(self):
  #   print(f'Opening connection to {self.port}...')

  #   try:
  #     self.reader, self.writer = await serial_asyncio.open_serial_connection(url=self.port, baudrate=self.baudrate)
      
  #     task = asyncio.ensure_future(self._read_handler())
  #     self.tasks.append(task)

  #   except Exception:
  #     print(traceback.format_exc())

  #   print(f'Connection to {self.port} is open.')

  # async def close(self):
  #   print(f'Closing connection to {self.port}')

  #   for task in self.tasks:
  #     task.cancel()
  #     await asyncio.gather(task)

  #   print(f'Closed connection to {self.port}')

  # async def _process_buffer(self):
  #   async for msg in self.buffer:
  #     msg = msg.decode("utf-8")
      
  #     self.write(msg)
  #     await sleep(0.01)

  # async def _buffer_output(self, msg):
  #   print(msg)

  # async def _read_handler(self):
  #   print("Read Handler")

  #   try:
  #     while True:
  #       msg = await self.reader.readuntil(b'\n')

  #       if self.readerCallback:
  #         await self.readerCallback(msg)
  #       else:
  #         await self._buffer_output(msg)

  #   except futures._base.CancelledError:
  #     print("Cancelled")
  #   except asyncio.streams.IncompleteReadError:
  #     print(traceback.format_exc())
  #   except Exception:
  #     print(traceback.format_exc())
