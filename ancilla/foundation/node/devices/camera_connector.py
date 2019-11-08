import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
from ..zhelpers import zpipe

import cv2

# class CameraConnector(object):
#   def __init__(self, ident, pub_endpoint, endpoint, baudrate, pipe, debug = True):
#     self.thread_read = None
#     self.publisher_endpoint = pub_endpoint
#     self.identity = ident
#     self.serial_endpoint = endpoint

#     ctx = zmq.Context.instance()   
#     socket = ctx.socket(zmq.PUB)
#     socket.bind(f'ipc://{self.identity}')

#     capture = cv2.VideoCapture('rtsp://192.168.1.64/1')
#     # socket.bind("tcp://*:5555")
#     self.video = cv2.VideoCapture(0)



class CameraConnector(object):
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time

    def __init__(self, ctx, identity, endpoint, **kwargs):  
      self.thread_read = None
      self.identity = identity
      self.endpoint = endpoint
      if self.endpoint.isnumeric():
        self.endpoint = int(self.endpoint)

      self.ctx = ctx

      

      self.create_camera()
      


    def create_camera(self):
      print("create camera", flush=True)
      self.video = cv2.VideoCapture(self.endpoint)

    
    def run(self):
      print("INSIDe RUN")
      # ctx = zmq.Context()

      self.alive = True
      if not self.thread_read or not self.thread_read.isAlive():
        self.thread_read = threading.Thread(target=self.reader, args=(self.ctx,))
        self.thread_read.daemon = True
        # self.thread_read.name = 'camera->reader'
        self.thread_read.start()

    def reader(self, ctx):
      print(f"RUN Camera SERVER: inproc://{self.identity}_collector", flush=True)
      publisher = ctx.socket(zmq.PUSH)
      publisher.connect(f"inproc://{self.identity}_collector")
      # publisher.connect("ipc://collector")
      # publisher.send_multipart([b'ender3', b'hello there'])
      # if self.endpoint
      # 'rtsp://192.168.1.64/1'
      # endpoint = self.endpoint.decode('utf-8')
      # if endpoint.isnumeric():
      #   endpoint = int(endpoint)
        
      # video = cv2.VideoCapture(endpoint)
      # camera = CameraConn(self.identity, "ipc://collector", self.endpoint.decode("utf-8"), self.baudrate, pipe)
      i=0
      # topic = 'camera_frame'
      while self.alive:
        try:
          
          ret, frame = self.video.read()
          # frame = video.read()
          # print("HI", ret)
          if ret:
            i += 1
          # publisher.send_multipart([self.identity, frame])
            publisher.send(self.identity, zmq.SNDMORE)
            publisher.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
            publisher.send_pyobj(frame)
            # time.sleep(2)
            # print('Sent frame {}'.format(i))
        except Exception as e:
          print(f'Exception with Camera: {str(e)}', flush=True)
          publisher.send_multipart([self.identity, b'error', str(e).encode('ascii')])
          break
      self.alive = False

    def open(self):
      try:
        if not self.video or not self.video.isOpened():
          # print(f"OPEN SERIAL {self.alive}", flush=True)
          # self
          self.create_camera()
          # self.serial = serial.Serial(self.port, self.baud_rate, timeout=4.0)
        # elif self.serial.is_closed:
        #   print("closeing IS OPEN")
        #   self.close()
      except Exception as e:
        print(f'Serial Open Exception {str(e)}')

    def close(self):
      """Stop copying"""
      print('stopping', flush=True)
      self.alive = False
      if self.thread_read:
          print("JOIN THREAD", flush=True)
          res = self.thread_read.join(4.0)
          if not self.thread_read.isAlive():
            self.thread_read = None

      try:
        # print("CLOSE SERIAL", flush=True)
        if self.video:          
          self.video.release()
          time.sleep(1)
          self.video = None
      except Exception as e:
        print(f"SErail close {str(e)}", flush=True)
      # finally:
      #   del self.serial
      #   self.serial = None
      
