import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
from ..api.zhelpers import zpipe

import cv2

class CameraConn(object):
  def __init__(self, ident, pub_endpoint, endpoint, baudrate, pipe, debug = True):
    self.publisher_endpoint = pub_endpoint
    self.identity = ident
    self.serial_endpoint = endpoint

    ctx = zmq.Context.instance()   
    socket = ctx.socket(zmq.PUB)
    socket.bind(f'icp://{self.identity}')

    capture = cv2.VideoCapture('rtsp://192.168.1.64/1')
    # socket.bind("tcp://*:5555")
    self.video = cv2.VideoCapture(0)
    # sleep(2)

    # i=0
    # topic = 'camera_frame'
    # while True:
    #     i += 1
    #     ret, frame = cap.read()
    #     socket.send_string(topic, zmq.SNDMORE)
    #     socket.send_pyobj(frame)
    #     print('Sent frame {}'.format(i))
    
    
    # self.baudrate = baudrate
    # print("endpoint = ", type(self.serial_endpoint))
    # print("BAUDRATE = ", type(baudrate))
    # # self.serial = serial.Serial('/dev/cu.usbserial-14140', 115200)
    # self.serial = serial.Serial(self.serial_endpoint, self.baudrate)
    # print(self.serial)
    # # ser = serial.serial_for_url(endpoint, do_not_open=True)
    # # ser.timeout = 3     # required so that the reader thread can exit
    # # reset control line as no _remote_ "terminal" has been connected yet
    # # ser.dtr = False
    # # ser.rts = False
    #   # self.serial = serial_instance
    # ctx = zmq.Context.instance()      
    # self.pipe = pipe
    # # self._write_lock = threading.Lock()
    # # self.rfc2217 = serial.rfc2217.PortManager(
    # #     self.serial,
    # #     self,
    # #     logger=logging.getLogger('rfc2217.server') if debug else None)
    # self.log = logging.getLogger('redirector')
    
    # # self.publisher_endpoint = "inproc://"
    # self.alive = True
    # self.thread_read = threading.Thread(target=self.reader, args=(ctx,))
    # self.thread_read.daemon = True
    # self.thread_read.name = 'serial->socket'
    # self.thread_read.start()
    # self.thread_poll = threading.Thread(target=self.statusline_poller)
    # self.thread_poll.daemon = True
    # self.thread_poll.name = 'status line poll'
    # self.thread_poll.start()

    # p_thread = Thread(target=publisher_thread)
    # s_thread = Thread(target=subscriber_thread)
    # p_thread.start()
    # s_thread.start()

    # pipe = zpipe(ctx)

    # subscriber = ctx.socket(zmq.XSUB)
    # subscriber.connect("tcp://localhost:6000")

    # publisher = ctx.socket(zmq.XPUB)
    # publisher.bind("tcp://*:6001")

    # l_thread = Thread(target=listener_thread, args=(pipe[1],))
    # l_thread.start()


  def reader(self, ctx):
      publisher = ctx.socket(zmq.PUSH)
      print("PUB ENDPOINT = ", self.publisher_endpoint)
      publisher.connect(self.publisher_endpoint)
      print("IDENTITY= ", self.identity)

      """loop forever and copy serial->socket"""
      self.log.debug('reader thread started')
      data = b''
      while self.alive:
          try:
              # data = self.serial.readuntil(b'\n')
              data += self.serial.read()
              if b'\n' in data:
                  print(data)
                  publisher.send_multipart([self.identity, data])
                  data = b''
                  # numLines = numLines + 1

              # if(numLines >= 1):
              #     break 
              # # data = self.serial.read(self.serial.in_waiting or 1)
              # print("INSIDE READER", flush=True)
              # if data:
              #     print(data)
              #     # escape outgoing data when needed (Telnet IAC (0xff) character)
              #     publisher.send_multipart([self.identity, data])
                  # self.write(b''.join(self.rfc2217.escape(data)))
          except socket.error as msg:
              self.log.error('{}'.format(msg))
              # probably got disconnected
              break
      self.alive = False
      self.log.debug('reader thread terminated')

  def stop(self):
      """Stop copying"""
      self.log.debug('stopping')
      if self.alive:
          self.alive = False
          self.thread_read.join()
          # self.thread_poll.join()      