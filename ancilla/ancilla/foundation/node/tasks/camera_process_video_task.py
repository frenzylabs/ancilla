'''
 camera_process_video_task.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/21/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.utils.monitor
# import zmq.asyncio
import json

from tornado.ioloop import IOLoop
# from zmq.eventloop.ioloop import PeriodicCallback
from ..zhelpers import zpipe
from ...data.models import PrintSlice, CameraRecording
# from .devices import *
from asyncio import sleep
# from tornado.gen        import sleep
from .ancilla_task import AncillaTask

from ...env import Env
from ..events.camera import Camera

import datetime
import pickle
import cv2
import numpy as np

import gc



class CameraProcessVideoTask(AncillaTask):

  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id
    self.current_frame = None
    self.current_framenum = None
    self.payload = payload
    self.camera_model = self.payload.get("camera") or {}
    self.camera_settings = self.camera_model.get("settings") or {}
    self.video_settings = self.camera_settings.get("video") or {"size": [640, 480]}
    width, height = self.video_settings.get("size") or [640, 480]
    self.video_size = (width, height)

    self.service = service
    self.state.update({"name": name, "status": "pending", "model": {}})


    self.processed_stream = f"ipc://{self.service.identity}_image_processor.ipc"
    self.processing_thread = None
    self.running = False
    self.current_frame = None

    
    image_collector = self.service.process.ctx.socket(zmq.SUB)
    image_collector.setsockopt(zmq.RCVHWM, 10)
    # image_collector.setsockopt(zmq.CONFLATE, 1)
    # image_collector.setsockopt(zmq.RCVBUF, 2*1024)

    image_collector.connect(self.service.process.pubsub_address)
    
    

    self.image_collector = ZMQStream(image_collector)
    self.image_collector.linger = 0
    self.image_collector.on_recv(self.on_data, copy=True)

    image_collector.setsockopt(zmq.SUBSCRIBE, b'data.camera.data_received')
    image_collector.setsockopt(zmq.SUBSCRIBE, b'events.camera.connection.closed')

    self.ready = True

    
  def on_data(self, msg):
    # identity, identifier, frm_num, frame = data
    if len(msg) != 4:
        # print(f"DATA = {msg[0]}", flush=True)
        # if 'bytes' in msg[0]:
        # if msg[0].bytes.endswith(b'connection.closed'):
        #     self.running = False
        #     self.state.status = "closed"
        if msg[0].endswith(b'connection.closed'):
          self.running = False
          self.state.status = "closed"
        return
    else:
      topic, identifier, framenum, imgdata = msg
      fnum = int(framenum.decode('utf-8'))
      # print(f"DATA = {topic}", flush=True)
      self.current_framenum = fnum
      self.current_frame = [topic, framenum, imgdata]


  async def run(self, *args):

    self.running = True
    self.state.status = "running"
    
    if not self.processing_thread or not self.processing_thread.isAlive():
        self.processing_thread = threading.Thread(target=self.process_images, args=(self.service.process.ctx,))
        self.processing_thread.daemon = True
        # self.thread_read.name = 'camera->reader'
        self.processing_thread.start()

    

    while self.state.status == "running":
        await sleep(1)

    print("FINISHED PROCESSING", flush=True)
    self.running = False
    self.image_collector.close()

    

  def process_images(self, ctx):
    # print(f"RUN Camera Image Processor SERVER: {self.processed_stream}", flush=True)

    self.publish_data = ctx.socket(zmq.XPUB)
    # self.publish_data.setsockopt(zmq.SNDHWM, 100)
    # self.publish_data.setsockopt(zmq.SNDBUF, 2*1024)
    self.publish_data.bind(self.processed_stream)

    # self._mon_socket = self.publish_data.get_monitor_socket(zmq.EVENT_CONNECTED | zmq.EVENT_DISCONNECTED)
    # self._mon_stream = ZMQStream(self._mon_socket)
    # self._mon_stream.on_recv(self._on_mon)
    
    self.timer = time.time()
    self.subsription_time = time.time()


    poller = zmq.Poller()
    # poller.register(image_collector, zmq.POLLIN)
    poller.register(self.publish_data, zmq.POLLIN)
    # poller.register(self._mon_socket, zmq.POLLIN)
    
    self.subscribers = {}
    
    framenum = 0
    while self.running:
      try:
        if len(self.subscribers.keys()) == 0 and (time.time() - self.subsription_time) > 10:
          self.state.status = "idle-close"
          break
          
        try:
            items = dict(poller.poll(1))
        except:
            break           # Interrupted4

        if framenum != self.current_framenum and self.current_frame:
          # if self.current_framenum - framenum > 1:
          #   print(f'Frame: l: {framenum}, cur: {self.current_framenum}')
          self.process_img(self.current_frame)
          framenum = self.current_framenum 

        if self.publish_data in items:
          
          event = self.publish_data.recv()
          if event[0] == 0:
            topic = event[1:]
            if topic in self.subscribers:
              del self.subscribers[topic]
              print(f"PUBLISH SOCKET has UNSubscribed {topic}")
              self.subsription_time = time.time()
          elif event[0] == 1:
            topic = event[1:]
            if len(topic) > 1:
              self.subscribers[topic] = time.time()
              print(f"PUBLISH SOCKET has subscribed {topic}")
          

      except Exception as e:
        print(f'Exception with Camera Process: {str(e)}', flush=True)
        if self.publish_data:
          self.publish_data.send_multipart([self.service.identity + b'.error', b'error', str(e).encode('ascii')], copy=True)
        # device_collector.send_multipart([self.identity, b'error', str(e).encode('ascii')])
        break
    if self.publish_data and self.state.status == "closed":
      try:
        self.publish_data.send_multipart([self.service.identity + b'.connection.closed', b"Connection Closed"], copy=True)
      except:
        pass

    
    self.publish_data.close()
    self.publish_data = None

  def process_img(self, data):
      topic, framenum, msg = data


      # fnum = int(framenum.decode('utf-8'))
      if not self.ready:
        return


      self.ready = False

      frame = pickle.loads(msg)
      # frame = np.frombuffer(frame, dtype="int8")
      # frame = np.fromstring(frame , np.uint8)
      frame = cv2.flip(frame, 1)
      # x = frame
      
      x = cv2.resize(frame, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      
      # # print(x.shape)
      # x = x.astype(np.uint8)
      # encodedImage = x
      (flag, encodedImage) = cv2.imencode(".jpg", x)

      ebytes = encodedImage.tobytes()
      
      try:
        self.publish_data.send_multipart([self.service.identity + b'.data', framenum, ebytes], copy=False)
      except Exception as e:
        print(f'Publish CamPV Exception {str(e)}', flush=True)
        # pass
      self.ready = True


  def _on_mon(self, msg):
      print("MONITOR SOCKET", msg)
      ev = zmq.utils.monitor.parse_monitor_message(msg)
      event = ev['event']
      endpoint = ev['endpoint']
      if event == zmq.EVENT_CONNECTED:
        print(f"CONNECTED {endpoint}")
        pass
          
      elif event == zmq.EVENT_DISCONNECTED:
        print(f"DISCONNECTED {endpoint}")
        pass
          

  def stop(self, *args):
    self.running = False
    self.close()

  def close(self, *args):    
    self.state.status = "closed"    
  
  def cancel(self):
    self.state.status = "cancelled"
  
  def finished(self):
    self.state.status = "finished"

  def pause(self):
    self.flush_callback.stop()
  
  def resume(self):
    self.flush_callback.start()
    # self.state.status = "paused"

  def get_state(self):
    self.service.fire_event(Camera.recording.state.changed, self.state)

