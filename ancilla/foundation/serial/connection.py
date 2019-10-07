'''
 serial_connection.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import serial
import time
import threading

from queue        import Queue
from types        import SimpleNamespace
from serial.tools import list_ports


class SerialConnection(object):
  _queue  = Queue()
  _thread = None
  websocket = None

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
    self.queue = Queue()


  def start(self):
    self._open()
    # self._run()
    self._thread = threading.Thread(target=self._run)
    # self._thread.setDaemon(True)
    self._thread.start()
   

  def _open(self):
    if not self.serial.port and self.serial.baudrate:
      raise ValueError('Port and baudrate are required for a serial connection')

    try:
      if self.serial.isOpen():
        self._close()

      self.serial.open() 
    except:
      raise


  def _close(self):
    try:
      self.serial.close()
    except:
      pass

  def _run(self):
    while self.serial.isOpen():
      self._read()

  def _read(self):
    while True:
      buffer = self.serial.readline().decode('utf-8')
      if len(buffer) > 0:
        self.websocket.emit('message', data=buffer)
      else:
        break

