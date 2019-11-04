import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
from ..zhelpers import zpipe
from ...data.models import Printer

class SerialConnector(object):
  def __init__(self, ctx, name, port, baud_rate, **kwargs):
    self.thread_read = None
    self.identity = name
    self.port = port
    self.baud_rate = baud_rate

    self.serial = serial.Serial(self.port, self.baud_rate)

    self.log = logging.getLogger('serial')
    self.ctx = ctx
    
    
  
  def start(self):
    print("INSIDe START")
    # ctx = zmq.Context()
    self.alive = True
    if not self.thread_read or not self.thread_read.isAlive():
      print("INSIDe thread read start")
      self.thread_read = threading.Thread(target=self.reader, args=(self.ctx,))
      self.thread_read.daemon = True
      self.thread_read.name = 'serial->reader'
      self.thread_read.start()
    # if not self.thread_writer or not self.thread_writer.isAlive():
    #   print("INSIDe thread read start")
    #   self.thread_writer = threading.Thread(target=self.writer, args=(self.ctx,))
    #   self.thread_writer.daemon = True
    #   self.thread_writer.name = 'serial->writer'
    #   self.thread_writer.start()

  def write(self, msg):
    self.serial.write(msg)

  def reader(self, ctx):
      publisher = ctx.socket(zmq.PUSH)
      publisher.connect(f"inproc://{self.identity}_collector")

      # publisher = ctx.socket(zmq.PUSH)
      # print("PUB ENDPOINT = ", self.publisher_endpoint)
      # publisher.bind(self.publisher_endpoint)
      # print("IDENTITY= ", self.identity)

      """loop forever and copy serial->socket"""
      self.log.debug('reader thread started')
      data = b''
      while self.alive:
          try:
              # data = self.serial.readuntil(b'\n')
              data += self.serial.read()
              if b'\n' in data:
                  publisher.send_multipart([self.identity, data])
                  data = b''
          except socket.error as msg:
              print('{}'.format(msg))
              # probably got disconnected
              publisher.send_multipart([self.identity, str(msg).encode('ascii')])
              break
      self.alive = False
      print('reader thread terminated', flush=True)


  def writer(self, ctx, pipe):
      publisher = ctx.socket(zmq.PUSH)
      publisher.connect(f"inproc://{self.identity}_collector")

      # publisher = ctx.socket(zmq.PUSH)
      # print("PUB ENDPOINT = ", self.publisher_endpoint)
      # publisher.bind(self.publisher_endpoint)
      # print("IDENTITY= ", self.identity)

      """loop forever and copy serial->socket"""
      self.log.debug('reader thread started')
      data = b''
      while self.alive:
          try:
              # data = self.serial.readuntil(b'\n')
              data += self.serial.read()
              if b'\n' in data:
                  publisher.send_multipart([self.identity, data])
                  data = b''
          except socket.error as msg:
              print('{}'.format(msg))
              # probably got disconnected
              publisher.send_multipart([self.identity, str(msg).encode('ascii')])
              break
      self.alive = False
      print('reader thread terminated', flush=True)

    
  def close(self):
      """Stop copying"""
      print('stopping', flush=True)
      self.serial.close()
      if self.alive:
          self.alive = False
          self.thread_read.join()
          # self.thread_poll.join()      

    # try:
    #     monitored_queue(subscriber, publisher, pipe[0], b'pub', b'sub')
    # except KeyboardInterrupt:
    #     print ("Interrupted")

