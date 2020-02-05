'''
 camera.py
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
import importlib
# from ..zhelpers import zpipe

# import cv2

import os
import shutil

import json


# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
# from ...base_service import BaseService
# from ....utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest
from .driver import CameraConnector
# from queue import Queue
# import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
# from zmq.eventloop.ioloop import PeriodicCallback

# from zmq.asyncio import Context, ZMQEventLoop

from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop, PeriodicCallback

import inspect
import asyncio
from types import CoroutineType

from tornado.platform.asyncio import AnyThreadEventLoopPolicy

import string, random



# from ..tasks.device_task import PeriodicTask
from ...tasks.camera_record_task import CameraRecordTask
from ...tasks.camera_process_video_task import CameraProcessVideoTask

from ...events import Event, EventPack, Service as EventService
from ...events.camera import Camera as CameraEvent
from ...events.event_pack import EventPack
from ...middleware.camera_handler import CameraHandler as CameraDataHandler
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError
from ...request import Request

from ....utils.delegate import DelegatedAttribute

# from multiprocessing import Process, Lock, Pipe, Value, Array
# import multiprocessing as mp


def yields(value):
    return isinstance(value, asyncio.futures.Future) or inspect.isgenerator(value) or \
           isinstance(value, CoroutineType)

    # @asyncio.coroutine
    # def call_maybe_yield(func, *args, **kwargs):
    #     rv = func(*args, **kwargs)
    #     if yields(rv):
    #         rv = yield from rv
    #     return rv

async def call_maybe_yield(func, *args, **kwargs):
    rv = func(*args, **kwargs)
    if yields(rv):
        rv = await rv
    return rv


class CameraHandler():
    # connector = None
    # endpoint = None         # Server identity/endpoint
    # identity = None
    # alive = True            # 1 if known to be alive
    # ping_at = 0             # Next ping at this time
    # expires = 0             # Expires at this time
    # state = "IDLE"
    # recording = False
    
    # command_queue = CommandQueue()
    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]
    connector = None
    video_processor = None
    # zmq_pub = None
    # zmq_router = None

    def __init__(self, process, **kwargs): 
      self.process = process
      self.camera_data_handler = CameraDataHandler(self)
      self.process.register_data_handlers(self.camera_data_handler)

    state = DelegatedAttribute('process', 'state')
    identity = DelegatedAttribute('process', 'identity')
    fire_event = DelegatedAttribute('process', 'fire_event')

    def close(self):
      if self.connector:
        self.connector.close()
      if self.video_processor:
        print(f"Close video processor")
        self.video_processor.close()
      self.process.fire_event(CameraEvent.connection.closed, self.state)
    

    def connect(self, data):
      endpoint = data.get("endpoint")
      print(f"Camera Connect {os.getpid()}", flush=True)
      if self.connector and self.connector.alive:
        return {"status": "connected"}

      self.connector = CameraConnector(self.process.ctx, self.process.identity, endpoint)
      self.connector.open()
      
      self.connector.run()
      self.state.connected = True
      print(f"Cam {os.getpid()} ")
      # tcr = CameraRecording(task_name="bob", settings={}, status="pending")
      # tcr.save()

      self.process.fire_event(CameraEvent.connection.opened, self.state)
      return {"status": "connected"}

    # def stop(self, *args):
    #   print("Camera Stop", flush=True)
    #   if self.connector:
    #     self.connector.close()
    #   self.connector = None
    #   # self.state.connected = False
    #   self.fire_event(CameraEvent.connection.closed, {"status": "success"})

    def get_or_create_video_processor(self, *args):
      # if not self.state.connected:
      #   raise AncillaError(400, {"error": "Camera Not Connected"})
      
      if self.video_processor:
          for k, v in self.process.current_tasks.items():
            if isinstance(v, CameraProcessVideoTask):    
              return {"stream": v.processed_stream}
              # return v

      # print(f'tc = {tcr}', flush=True)
      payload = {"settings": {}}
      self.video_processor = CameraProcessVideoTask("process_video", self.process, payload)
      self.process.add_task(self.video_processor)
      # self.process.task_queue.put(self.video_processor)
      # loop = IOLoop().current()
      # loop.add_callback(partial(self._process_tasks))
      return {"stream": self.video_processor.processed_stream}


    def get_recording_task(self, data):
      try:

        task_name = data.get("task_name")
        cr = None
        if data.get("recording_id"):
          cr = CameraRecording.get_by_id(data.get("recording_id"))
          task_name = cr.task_name

        printmodel = data.get("model")
      
        for k, v in self.process.current_tasks.items():
          print(f"TASKkey = {k} and v = {v}", flush=True)
          if isinstance(v, CameraRecordTask):
            if printmodel:
              if v.recording.print_id == printmodel.get("id"):
                return v
            if task_name:
              if k == task_name:
                return v
            else:
              return v
        return None #self.current_task.get(task_name)

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    def stop_recording(self, msg):
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.cancel()
          self.state.recording = False
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

    def pause_recording(self, msg):
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.pause()
          self.state.recording = False
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

    def resume_recording(self, msg):
      try:
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.resume()
          self.state.recording = True
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant resume recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not resume task {str(e)}"}

    def start_recording(self, msg):
      print(f"START RECORDING {msg}", flush=True)
      # print(f"RECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      # return {"started": True}
      try:

        payload = msg.get('data')
        name = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))

        pt = CameraRecordTask(name, self.process, payload)
        self.process.add_task(pt)
        self.state.recording = True
        # self.task_queue.put(pt)
        # loop = IOLoop().current()
        # loop.add_callback(partial(self._process_tasks))
        return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        raise AncillaError(400, {"status": "error", "error": f"Could not record {str(e)}"}, exception=e)
        # return {"status": "error", "error": f"Could not record {str(e)}"}

    




