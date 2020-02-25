'''
 camera_record_task.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
# import zmq.asyncio
import json

from tornado.ioloop import IOLoop, PeriodicCallback
# from zmq.eventloop.ioloop import PeriodicCallback
from ..zhelpers import zpipe
from ...data.models import PrintSlice, CameraRecording
# from .devices import *
# from tornado.gen        import sleep
from asyncio import sleep
from .ancilla_task import AncillaTask

from ...env import Env
from ..events.camera import Camera

import datetime
import pickle
import cv2
import numpy as np

import gc

class CameraRecordTask(AncillaTask):
  def __init__(self, name, service, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id
    self.payload = payload
    self.camera_model = payload.get('camera_model')
    self.task_settings = self.payload.get("settings") or {}
    self.service = service
    self.state.update({"name": name, "status": "pending", "model": {}})
    
    self.root_path = "/".join([self.service.model.directory, "recordings", self.name])
    if not os.path.exists(self.root_path):
      os.makedirs(self.root_path)
    self.image_path = self.root_path + "/images"
    if not os.path.exists(self.image_path):
      os.makedirs(self.image_path)
    self.video_path = self.root_path + "/videos"
    if not os.path.exists(self.video_path):
      os.makedirs(self.video_path)
    
    
    self.recording = CameraRecording(task_name=name, image_path=self.image_path, video_path=self.video_path, settings=self.task_settings, status="pending")

    if not self.camera_model:
      return
      
    self.recording.camera_snapshot = self.camera_model
    self.recording.camera_id = self.camera_model["id"] #self.service.camera_model

    printmodel = self.payload.get("model")
    if printmodel:
      if printmodel.get("id"):
        self.recording.print_id = printmodel.get("id")

    self.recording.save(force_insert=True) 
    # self.name = self.recording.id

    print(f"CR root path = {self.root_path}")

    
    processor = self.service.get_or_create_video_processor({"camera": self.camera_model})
    if not processor:
      return 

    self.current_frame_num = 0
    self.current_frame = None

    event_socket = self.service.process.ctx.socket(zmq.SUB)
    # event_socket.setsockopt(zmq.RCVHWM, 2)
    
    # event_socket.setsockopt(zmq.RCVBUF, 1*1024)
    event_socket.connect(processor.get("stream"))
    

    self.event_stream = ZMQStream(event_socket)
    self.event_stream.linger = 0
    self.event_stream.on_recv(self.on_data, copy=False)
    event_socket.setsockopt(zmq.SUBSCRIBE, self.name.encode('ascii'))
    event_socket.setsockopt(zmq.SUBSCRIBE, b'')

    
    self.retry = 5
    self.missed_frames = 0
    # ["wessender", "start_print", {"name": "printit", "file_id": 1}]

  # return [b'events.camera.data_received', identifier, frm_num, frame]
  def on_data(self, data):
    # identity, identifier, frm_num, frame = data
    if len(data) == 3:
      
    # print("CR Task, ON DATA", flush=True)
      # gc.collect()
      # self.current_frame = imgdata
      if  not self.current_frame:
        topic, framenum, imgdata = data
        # self.current_frame = imgdata
        self.current_frame = imgdata.bytes
      # else:
      #   print(f'Received but no processing')
    else:
      print("CONNECTINO CLOSED")
      if data[0].bytes.endswith(b'connection.closed'):
        self.state.status = "finished"
        self.state.reason = "Connection Disconnected"
      # if data[0].endswith(b'connection.closed'):
      #   self.state.status = "finished"
      #   self.state.reason = "Connection Disconnected"

  def flush_camera_frame(self):
    try:
      curtime = time.time()
      if not self.current_frame:
        if self.missed_frames > 10:
          self.state.status = "failed"
          self.state.reason = "Too many missed frames"
          self.state.recording = False
        self.missed_frames += 1  
        return
      self.missed_frames = 0
      # imgname = f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-{self.current_frame_num:06}.jpg'
      # frame = pickle.loads(self.current_frame)
      # frame = cv2.flip(frame, 1)
      # nparr = np.fromstring(self.current_frame, np.uint8)
      # x = self.current_frame.bytes
      # x = cv2.imdecode(self.current_frame, cv2.IMREAD_COLOR)
      nparr = np.frombuffer(self.current_frame, np.uint8)
      # x = cv2.resize(nparr, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      x = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
      # x = cv2.resize(x, dsize=self.video_size, interpolation=cv2.INTER_CUBIC)
      # print(x.shape)

      # x = x.astype(np.uint8)
      # (flag, encodedImage) = cv2.imencode(".jpg", x)
  
      # cv2.imwrite(self.image_path+"/"+imgname, x)
      if self.video_writer:
        self.video_writer.write(x)
      self.current_frame_num += 1
      self.current_frame = None
      res = time.time() - curtime
      # print(f"cam recording flush tooke {res}", flush=True)
    except Exception as e:
      print(f"Error saving camera frame {str(e)}", flush=True)
      if self.retry > 0:
        self.retry -= 1
      else:
        self.state.status = "failed"
        self.state.reason = str(e)
        self.state.recording = False
        
        
    
  async def run(self, dv):
    try:
      defaul_cam_settings = {
        "record": {
          "timelapse": 2,
          "frames_per_second": 10,
        },
        "video": {
          "size": [640, 480],
          "format": "avc1"
        }
      }
      cam_settings = self.camera_model.get("settings", defaul_cam_settings)
      
      
      
      record_settings = cam_settings.get("record", {})
      self.timelapse = int(record_settings.get("timelapse") or 2)
      self.timelapse = int(self.task_settings.get("timelapse") or self.timelapse)
      self.video_fps = int(record_settings.get("frames_per_second") or 10)
      self.video_fps = int(self.task_settings.get("frames_per_second") or self.video_fps)

      video_settings = cam_settings.get("video", {})
      width, height = video_settings.get("size") or [640, 480]
      self.video_size = (width, height)
      self.video_format = video_settings.get("format") or "avc1" #"X264"
      self.video_path = self.video_path + "/output.mp4"
      

      self.video_writer = cv2.VideoWriter(self.video_path, cv2.VideoWriter_fourcc(*self.video_format), self.video_fps, self.video_size)


      self.state.status = "recording"
      self.recording.status = self.state.status
      self.recording.video_path = self.video_path
      self.recording.save()
      self.state.model = self.recording
      self.state.id = self.recording.id
      
      self.service.fire_event(Camera.recording.started, self.state)

      flush_frame_check = self.timelapse * 1000
      if self.timelapse == 0:
        # self.timelapse = 1000      
        flush_frame_check = int(1000 / self.video_fps)

      self.flush_callback = PeriodicCallback(self.flush_camera_frame, flush_frame_check, 0.1)
      self.flush_callback.start()
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant record from camera {str(e)}", flush=True)
      self.state.status = "failed"
      self.state.reason = f"Cant record from camera {str(e)}"
      self.service.fire_event(Camera.recording.failed, {"status": "failed", "reason": str(e)})
      # return {"status": "failed"}

    # self.state.status = "running"
    while self.state.status == "recording":
      await sleep(0.5)


    return self.cleanup()

  def cleanup(self):
    print("FINSIHED RECORDING", flush=True)

    self.recording.status = "finished"
    self.recording.reason = self.state.reason or ""
    self.recording.save()
    self.service.state.recording = False
    self.service.fire_event(Camera.recording.state.changed, self.state)
    
    self.flush_callback.stop()
    self.event_stream.close()
    if self.video_writer:
      self.video_writer.release()
      self.video_writer = None
    return {"state": self.state}

  def stop(self, *args):
    self.finished()
    self.cleanup()
    
    
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
    
    # self.publish_request(request)
  
