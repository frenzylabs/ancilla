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

import os
import ctypes



class CameraConnector(object):
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time

    def __init__(self, ctx, identity, camera, **kwargs):  
      self.thread_read = None
      self.identity = identity
      self.camera = camera
      self.endpoint = camera.get("endpoint")
      self.settings = camera.get("settings")

      self.logger = logging.getLogger(camera.get("name"))

      if isinstance(self.endpoint, str) and self.endpoint.isnumeric():
        self.endpoint = int(self.endpoint)
      if self.endpoint == "-1":
        self.endpoint = -1

      self.ctx = ctx
      self.create_camera()

      try:
        self.redirect_stderr()
      except:
        pass
      

    def redirect_stderr(self):
      libc = ctypes.CDLL(None)
      c_stderr = ctypes.c_void_p.in_dll(libc, 'stderr')
      original_stderr_fd = sys.stderr.fileno()
      f = open(os.devnull, 'w')
      to_fd = f.fileno()
      libc.fflush(c_stderr)
      sys.stderr.close()
      os.dup2(to_fd, original_stderr_fd)
      sys.stderr = os.fdopen(original_stderr_fd)


    def create_camera(self):
      self.logger.debug("CREATE CAMERA HERE")
      self.video = VideoCapture(self.endpoint)
      
      videosettings = self.settings.get("video", {})


      fourcc = videosettings.get("CAP_PROP_FOURCC")
      if fourcc == None:
        fourcc = 'MJPG'
      if len(fourcc) == 4:
        self.video.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*fourcc))
        del videosettings["CAP_PROP_FOURCC"]

      for prop, val in videosettings.items():
        if prop.startswith('CAP_PROP') and val != "":
          self.set_capture_prop(prop, val)


      time.sleep(0.5)
      if not self.video.isOpened():
        self.video.release()
        self.video = None
        raise Exception(f"Could Not Open Video with Endpoint {self.endpoint}")
      
    def set_capture_prop(self, prop, val):
      try:
        self.video.set(getattr(cv2, prop), val)
      except: 
        pass


    def list_supported_capture_properties(self):
      """ List the properties supported by the capture device.
      """
      supported = list()
      for attr in dir(cv2):
          if attr.startswith('CAP_PROP'):
            supported.append(attr)              
      return supported
    
    def run(self):
      self.alive = True
      if not self.thread_read or not self.thread_read.isAlive():
        self.thread_read = threading.Thread(target=self.reader, args=(self.ctx,))
        self.thread_read.daemon = True
        # self.thread_read.name = 'camera->reader'
        self.thread_read.start()

    def reader(self, ctx):
      device_collector = ctx.socket(zmq.PUSH)
      device_collector.connect(f"inproc://{self.identity}_collector")
    
      i=0

      retry = 0
      max_retry_cnt = 10
      
      while self.alive:
        try:
          
          res = self.video.read()
          if not res:        
            if retry < max_retry_cnt:
              retry += 1
              time.sleep(1)
              continue
            print(f'1 CAMERA DISCONNECTED retrycnt {retry}', flush=True)
            raise Exception("1 Camera Disconnected")
          
          ret, frame = res
          if ret:
            i += 1
            retry = 0
            # print(f'frame = {frame}')
          # publisher.send_multipart([self.identity, frame])
            device_collector.send_multipart([self.identity + b'.data_received', f'{i}'.encode('ascii'), pickle.dumps(frame, -1)])
          else:
            if retry < max_retry_cnt:
              retry += 1
              time.sleep(0.5)
              continue
            
            print(f'CAMEA DISCONNECTED retrycnt {retry}', flush=True)
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
          self.alive = False
          self.close_video()
          break
      device_collector.close()
      device_collector = None
      self.alive = False

    def open(self):
      try:
        if not self.video or not self.video.isOpened():
          self.create_camera()

      except Exception as e:
        print(f'Serial Open Exception {str(e)}')

    def close_video(self):
      try:
        print("CLOSE VIDEO", flush=True)
        if self.video:          
          self.video.release()
          time.sleep(0.3)
          self.video = None
      except Exception as e:
        print(f"Serial close {str(e)}", flush=True)

    def close(self):
      """Stop copying"""
      self.alive = False
      if self.thread_read:
          res = self.thread_read.join(2.0)
          if not self.thread_read.isAlive():
            self.thread_read = None

      self.close_video()

