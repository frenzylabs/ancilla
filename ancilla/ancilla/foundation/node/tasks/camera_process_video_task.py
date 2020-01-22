import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.utils.monitor
import zmq.asyncio
import json

from tornado.ioloop import IOLoop
from zmq.eventloop.ioloop import PeriodicCallback
from ..zhelpers import zpipe
from ...data.models import PrintSlice, CameraRecording
# from .devices import *
from tornado.gen        import sleep
from .ancilla_task import AncillaTask

from ...utils import Dotdict
from ...env import Env
from ..events.camera import Camera

import datetime
import pickle
import cv2
import numpy as np

import gc



class CameraProcessVideoTask(AncillaTask):
  current_frame = None
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id
    self.payload = payload
    self.task_settings = self.payload.get("settings") or {}
    self.settings = self.task_settings.get("settings") or {"size": [640, 480]}
    width, height = self.settings.get("size") or [640, 480]
    self.video_size = (width, height)

    # self.timelapse = int(self.task_settings.get("timelapse") or 2) * 1000
    
    # self.video_settings = self.task_settings.get("videoSettings") or {"format": "mp4v"}
    # self.video_format = self.video_settings.get("format") or "mp4v"      
    # self.video_fps = int(self.video_settings.get("fps") or 10)

    self.service = service
    # self.state = Dotdict({"status": "pending", "model": {}})
    self.state.update({"name": name, "status": "pending", "model": {}})


    self.processed_stream = f"ipc://{self.service.identity}_image_processor"
    self.processing_thread = None
    self.running = False
    self.current_frame = None

    image_collector = self.service.ctx.socket(zmq.SUB)
    image_collector.connect(f"ipc://publisher")

    self.image_collector = ZMQStream(image_collector)
    self.image_collector.linger = 0
    self.image_collector.on_recv(self.on_data, copy=True)

    image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.data_received')
    image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.connection.closed')

    self.ready = True
    # self.flush_callback = PeriodicCallback(self.flush_camera_frame, 20)
    # self.flush_callback.start()
    
  def on_data(self, msg):
    # identity, identifier, frm_num, frame = data
    if len(msg) != 4:
        print(f"DATA = {msg[0]}", flush=True)
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
    # print("CR Task, ON DATA", flush=True)
      # if self.ready:      
      self.current_frame = [topic, framenum, imgdata]


  async def run(self, *args):
    print("INSIDe ProcessVideo RUN")
    # ctx = zmq.Context()

    self.running = True
    self.state.status = "running"
    
    if not self.processing_thread or not self.processing_thread.isAlive():
        self.processing_thread = threading.Thread(target=self.process_images, args=(self.service.ctx,))
        self.processing_thread.daemon = True
        # self.thread_read.name = 'camera->reader'
        self.processing_thread.start()

    

    while self.state.status == "running":
        await sleep(0.1)
    print("FINISHED PROCESSING", flush=True)
    self.running = False
    self.image_collector.close()

    

  def process_images(self, ctx):
    print(f"RUN Camera Image Processor SERVER: {self.processed_stream}", flush=True)
    # image_collector = ctx.socket(zmq.SUB)
    # image_collector.connect(f"ipc://publisher")
    
    # image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.data_received')
    # image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.connection.closed')

    self.publish_data = ctx.socket(zmq.XPUB)
    self.publish_data.bind(self.processed_stream)

    # self._mon_socket = self.publish_data.get_monitor_socket(zmq.EVENT_CONNECTED | zmq.EVENT_DISCONNECTED)
    # self._mon_stream = ZMQStream(self._mon_socket)
    # self._mon_stream.on_recv(self._on_mon)
    
    self.timer = time.time()
    # self.ready = True
    
    self.subsription_time = time.time()


    poller = zmq.Poller()
    # poller.register(image_collector, zmq.POLLIN)
    poller.register(self.publish_data, zmq.POLLIN)
    # poller.register(self._mon_socket, zmq.POLLIN)
    
    self.subscribers = {}
    
    while self.running:
      try:
        if len(self.subscribers.keys()) == 0 and (time.time() - self.subsription_time) > 10:
          print("NO SUBSCRIBERS", flush=True)
          self.state.status = "idle-close"
          break
          
        try:
            items = dict(poller.poll(10))
        except:
            break           # Interrupted4

        if self.current_frame:
          self.process_img(self.current_frame)
          gc.collect()

        # if image_collector in items:
        #     # print("INSIDE AGENT PIPE", flush=True)          
        #     data = image_collector.recv_multipart()
        #     self.process_img(data)

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
          


        # publish_data.send(self.identity + b'.data_received', zmq.SNDMORE)
        # publish_data.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
        # publish_data.send_pyobj(ebytes)
        # else:
        #   if not self.video.isOpened():
        #     print("VIDEO IS NOT OPENED", flush=True)
          # time.sleep(2)
          # print('Sent frame {}'.format(i))
      except Exception as e:
        print(f'Exception with Camera Process: {str(e)}', flush=True)
        if self.publish_data:
          self.publish_data.send_multipart([self.service.identity + b'.error', b'error', str(e).encode('ascii')], copy=True)
        # device_collector.send_multipart([self.identity, b'error', str(e).encode('ascii')])
        self.alive = False
        break
    if self.publish_data and self.state.status == "closed":
      try:
        self.publish_data.send_multipart([self.service.identity + b'.connection.closed', b"Connection Closed"], copy=True)
      except:
        pass

    self.alive = False
    self.publish_data.close()
    self.publish_data = None

  def process_img(self, data):
      # if len(data) != 4:
      #   if data[0].endswith(b'connection.closed'):
      #     self.running = False
      #     self.state.status = "closed"
      #   return


      topic, framenum, msg = data


      # fnum = int(framenum.decode('utf-8'))
      if not self.ready:
        # print(f"Not ready {fnum} {self}")
        return

      
      # if (fnum % 100) == 0:
      # timedif = time.time() - self.timer
      # if timedif > 0.01:
      #   self.timer = time.time()
      #   # print(f"fRAME = {fnum} {timedif},  {self.timer}")
        
      # else:
      #   # print(f"NOtReady fRAME = {fnum} {timedif},  {self.timer}")
      #   return

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
      
      # frame = video.read()
      # print(f"Publishdata {fnum} {len(ebytes)}")
      
      self.publish_data.send_multipart([self.service.identity + b'.data', framenum, ebytes], copy=False)
      self.ready = True

  # def process_img(self, data):
  #     if len(data) != 4:
  #       if data[0].endswith(b'connection.closed'):
  #         self.running = False
  #         self.state.status = "closed"
  #       return


  #     topic, device, framenum, msg = data


  #     fnum = int(framenum.decode('utf-8'))
  #     if not self.ready:
  #       # print(f"Not ready {fnum} {self}")
  #       return

      
  #     # if (fnum % 100) == 0:
  #     timedif = time.time() - self.timer
  #     if timedif > 0.01:
  #       self.timer = time.time()
  #       # print(f"fRAME = {fnum} {timedif},  {self.timer}")
        
  #     else:
  #       # print(f"NOtReady fRAME = {fnum} {timedif},  {self.timer}")
  #       return

  #     self.ready = False

  #     frame = pickle.loads(msg)
      
  #     frame = cv2.flip(frame, 1)
  #     # x = frame
      
  #     x = cv2.resize(frame, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      
  #     # # print(x.shape)
  #     # x = x.astype(np.uint8)
  #     # encodedImage = x
  #     (flag, encodedImage) = cv2.imencode(".jpg", x)

  #     ebytes = encodedImage.tobytes()
      
  #     # frame = video.read()
  #     # print(f"Publishdata {fnum} {len(ebytes)}")
      
  #     self.publish_data.send_multipart([self.service.identity + b'.data', framenum, ebytes])
  #     self.ready = True
    

  def _on_mon(self, msg):
      print("MONITOR SOCKET")
      print(f"MONEVENT= {msg}")
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
    # self.device.add_command(request_id, 0, 'M0\n', True, True)

  def pause(self):
    self.flush_callback.stop()
  
  def resume(self):
    self.flush_callback.start()
    # self.state.status = "paused"

  def get_state(self):
    print("get state", flush=True)
    self.state.model = self.service.current_print.json
    self.service.fire_event(Camera.recording.state.changed, self.state)
    
    # self.publish_request(request)
  


# import threading
# import time
# import sys
# import os
# import zmq
# from zmq.eventloop.zmqstream import ZMQStream
# import zmq.utils.monitor
# import zmq.asyncio
# import json

# from tornado.ioloop import IOLoop
# from zmq.eventloop.ioloop import PeriodicCallback
# from ..zhelpers import zpipe
# from ...data.models import PrintSlice, CameraRecording
# # from .devices import *
# from tornado.gen        import sleep
# from .ancilla_task import AncillaTask

# from ...utils import Dotdict
# from ...env import Env
# from ..events.camera import Camera

# import datetime
# import pickle
# import cv2
# import numpy as np



# class CameraProcessVideoTask(AncillaTask):
#   def __init__(self, name, service, payload, *args):
#     super().__init__(name, *args)
#     # self.request_id = request_id
#     self.payload = payload
#     self.task_settings = self.payload.get("settings") or {}
#     self.settings = self.task_settings.get("settings") or {"size": [640, 480]}
#     width, height = self.settings.get("size") or [640, 480]
#     self.video_size = (width, height)

#     # self.timelapse = int(self.task_settings.get("timelapse") or 2) * 1000
    
#     # self.video_settings = self.task_settings.get("videoSettings") or {"format": "mp4v"}
#     # self.video_format = self.video_settings.get("format") or "mp4v"      
#     # self.video_fps = int(self.video_settings.get("fps") or 10)

#     self.service = service
#     # self.state = Dotdict({"status": "pending", "model": {}})
#     self.state.update({"name": name, "status": "pending", "model": {}})


#     self.processed_stream = f"ipc://{self.service.identity}_image_processor"
#     self.processing_thread = None
#     self.running = False
    

#   async def run(self, *args):
#     print("INSIDe ProcessVideo RUN")
#     # ctx = zmq.Context()

#     self.running = True
#     self.state.status = "running"
    
#     if not self.processing_thread or not self.processing_thread.isAlive():
#         self.processing_thread = threading.Thread(target=self.process_images, args=(self.service.ctx,))
#         self.processing_thread.daemon = True
#         # self.thread_read.name = 'camera->reader'
#         self.processing_thread.start()

    

#     while self.state.status == "running":
#         await sleep(0.1)
#     print("FINISHED PROCESSING", flush=True)
#     self.running = False

    

#   def process_images(self, ctx):
#     print(f"RUN Camera Image Processor SERVER: {self.processed_stream}", flush=True)
#     image_collector = ctx.socket(zmq.SUB)
#     image_collector.connect(f"ipc://publisher")
    
#     image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.data_received')
#     image_collector.setsockopt(zmq.SUBSCRIBE, self.service.identity + b'.events.camera.connection.closed')

#     self.publish_data = ctx.socket(zmq.XPUB)
#     self.publish_data.bind(self.processed_stream)

#     # self._mon_socket = self.publish_data.get_monitor_socket(zmq.EVENT_CONNECTED | zmq.EVENT_DISCONNECTED)
#     # self._mon_stream = ZMQStream(self._mon_socket)
#     # self._mon_stream.on_recv(self._on_mon)
    
#     self.timer = time.time()
#     self.ready = True
    
#     self.subsription_time = time.time()


#     poller = zmq.Poller()
#     poller.register(image_collector, zmq.POLLIN)
#     poller.register(self.publish_data, zmq.POLLIN)
#     # poller.register(self._mon_socket, zmq.POLLIN)
    
#     self.subscribers = {}
    
#     while self.running:
#       try:
#         if len(self.subscribers.keys()) == 0 and (time.time() - self.subsription_time) > 30:
#           print("NO SUBSCRIBERS", flush=True)
#           self.state.status = "idle-close"
#           break
          
#         try:
#             items = dict(poller.poll(1000))
#         except:
#             break           # Interrupted4

#         if image_collector in items:
#             # print("INSIDE AGENT PIPE", flush=True)          
#             data = image_collector.recv_multipart()
#             self.process_img(data)

#         if self.publish_data in items:
          
#           event = self.publish_data.recv()
#           if event[0] == 0:
#             topic = event[1:]
#             if topic in self.subscribers:
#               del self.subscribers[topic]
#               print(f"PUBLISH SOCKET has UNSubscribed {topic}")
#               self.subsription_time = time.time()
#           elif event[0] == 1:
#             topic = event[1:]
#             if len(topic) > 1:
#               self.subscribers[topic] = time.time()
#               print(f"PUBLISH SOCKET has subscribed {topic}")
          


#         # publish_data.send(self.identity + b'.data_received', zmq.SNDMORE)
#         # publish_data.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
#         # publish_data.send_pyobj(ebytes)
#         # else:
#         #   if not self.video.isOpened():
#         #     print("VIDEO IS NOT OPENED", flush=True)
#           # time.sleep(2)
#           # print('Sent frame {}'.format(i))
#       except Exception as e:
#         print(f'Exception with Camera: {str(e)}', flush=True)
#         if self.publish_data:
#           self.publish_data.send_multipart([self.service.identity + b'.data', b'error', str(e).encode('ascii')])
#         # device_collector.send_multipart([self.identity, b'error', str(e).encode('ascii')])
#         self.alive = False
#         break
#     self.alive = False

  
#   def process_img(self, data):
#       if len(data) != 4:
#         if data[0].endswith(b'connection.closed'):
#           self.running = False
#           self.state.status = "closed"
#         return


#       topic, device, framenum, msg = data


#       fnum = int(framenum.decode('utf-8'))
#       if not self.ready:
#         # print(f"Not ready {fnum} {self}")
#         return

      
#       # if (fnum % 100) == 0:
#       timedif = time.time() - self.timer
#       if timedif > 0.01:
#         self.timer = time.time()
#         # print(f"fRAME = {fnum} {timedif},  {self.timer}")
        
#       else:
#         # print(f"NOtReady fRAME = {fnum} {timedif},  {self.timer}")
#         return

#       self.ready = False

#       frame = pickle.loads(msg)
      
#       frame = cv2.flip(frame, 1)
#       # x = frame
      
#       x = cv2.resize(frame, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      
#       # # print(x.shape)
#       # x = x.astype(np.uint8)
#       # encodedImage = x
#       (flag, encodedImage) = cv2.imencode(".jpg", x)

#       ebytes = encodedImage.tobytes()
      
#       # frame = video.read()
#       # print(f"Publishdata {fnum} {len(ebytes)}")
      
#       self.publish_data.send_multipart([self.service.identity + b'.data', framenum, ebytes])
#       self.ready = True
    

#   def _on_mon(self, msg):
#       print("MONITOR SOCKET")
#       print(f"MONEVENT= {msg}")
#       ev = zmq.utils.monitor.parse_monitor_message(msg)
#       event = ev['event']
#       endpoint = ev['endpoint']
#       if event == zmq.EVENT_CONNECTED:
#         print(f"CONNECTED {endpoint}")
#         pass
          
#       elif event == zmq.EVENT_DISCONNECTED:
#         print(f"DISCONNECTED {endpoint}")
#         pass
          

#   def close(self, *args):
#     self.state.status = "closed"    

#   def cancel(self):
#     self.state.status = "cancelled"
  
#   def finished(self):
#     self.state.status = "finished"
#     # self.device.add_command(request_id, 0, 'M0\n', True, True)

#   def pause(self):
#     self.flush_callback.stop()
  
#   def resume(self):
#     self.flush_callback.start()
#     # self.state.status = "paused"

#   def get_state(self):
#     print("get state", flush=True)
#     self.state.model = self.service.current_print.json
#     self.service.fire_event(Camera.recording.state.changed, self.state)
    
#     # self.publish_request(request)
  
