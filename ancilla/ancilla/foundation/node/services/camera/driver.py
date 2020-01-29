'''
 driver.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq

from cv2 import cv2, VideoCapture
import imp
import pickle 

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
      # if not isinstance(self.endpoint, (int, float, complex)) and not isinstance(self.endpoint, bool):
      # imp.find_module("cv2")
      # import cv2
      # cvmodule = sys.modules.get("cv2")
      # print(sys.modules.get("cv2"))
      # print(VideoCapture)
      # reload(sys.modules.get("cv2"))
      # importlib.reload(cv2)
      

      if isinstance(self.endpoint, str) and self.endpoint.isnumeric():
        self.endpoint = int(self.endpoint)
      if self.endpoint == "-1":
        self.endpoint = -1

      self.ctx = ctx
      self.create_camera()
      

    def create_camera(self):
      print("create camera", flush=True)
      self.video = VideoCapture(self.endpoint)
      if not self.video.isOpened():
        self.video.release()
        self.video = None
        raise Exception(f"Could Not Open Video with Endpoint {self.endpoint}")
      

    
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
      device_collector = ctx.socket(zmq.PUSH)
      device_collector.connect(f"inproc://{self.identity}_collector")
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
          
          res = self.video.read()
          if not res:            
            raise "Camera Disconnected"
          ret, frame = res
          # frame = video.read()
          
          if ret:
            i += 1
            # print(f'frame = {frame}')
          # publisher.send_multipart([self.identity, frame])
            device_collector.send_multipart([self.identity + b'.data_received', f'{i}'.encode('ascii'), pickle.dumps(frame, -1)])
          else:
            raise Exception("Camera Disconnected")
            
            # device_collector.send(self.identity + b'.data_received', zmq.SNDMORE)
            # device_collector.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
            # device_collector.send_pyobj(frame)
          # else:
          #   if not self.video.isOpened():
          #     print("VIDEO IS NOT OPENED", flush=True)
            # time.sleep(2)
            # print('Sent frame {}'.format(i))
        except Exception as e:
          print(f'Exception with Camera Driver: {str(e)}', flush=True)
          device_collector.send_multipart([self.identity + b'.data_received', b'error', str(e).encode('ascii')])
          # device_collector.send_multipart([self.identity, b'error', str(e).encode('ascii')])
          self.alive = False
          break
      device_collector.close()
      device_collector = None
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
          res = self.thread_read.join(2.0)
          if not self.thread_read.isAlive():
            self.thread_read = None

      try:
        print("CLOSE SERIAL", flush=True)
        if self.video:          
          self.video.release()
          time.sleep(1)
          self.video = None
      except Exception as e:
        print(f"SErail close {str(e)}", flush=True)
      # finally:
      #   del self.serial
      #   self.serial = None
      
