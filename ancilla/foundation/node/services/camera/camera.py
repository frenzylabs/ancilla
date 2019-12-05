import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
# from ..zhelpers import zpipe

# import cv2

import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop

# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
from ...base_service import BaseService

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
from zmq.eventloop.ioloop import PeriodicCallback
import string, random



# from ..tasks.device_task import PeriodicTask
from ...tasks.camera_record_task import CameraRecordTask
from ...events.camera import Camera as CameraEvent
from ...middleware.camera_handler import CameraHandler
from ...api.camera import CameraApi
    

class Camera(BaseService):
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
      "stop_recording"
    ]

    def __init__(self, model, **kwargs):
        # self.camera_model = CameraModel.get(CameraModel.name == name)
        self.camera_model = CameraModel.get(CameraModel.service == model)
        # self.task_queue = Queue()
        # self.port = self.record['port']
        # self.baud_rate = self.record['baud_rate']

        
        super().__init__(model, **kwargs)        
        self.camera_handler = CameraHandler(self)
        self.register_data_handlers(self.camera_handler)
        self.api = CameraApi(self)
        self.connector = None

        self.event_class = CameraEvent

        self.state.load_dict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "recording": False
        })

        # self.register_data_handlers(PrinterHandler(self))

    # def actions(self):
    #   return [
    #     "record"
    #   ]

    def start(self, *args):
      print(f"START Camera {self.identity}", flush=True)
      self.connector = CameraConnector(self.ctx, self.identity, self.camera_model.endpoint)
      # self.connector.start()
    
    def connect(self, *args):
      try:
        if not self.connector:
          self.start()
        #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
        # else:
        self.connector.open()
        print("Camera Connect", flush=True)
        self.connector.run()
        self.fire_event(CameraEvent.connection.opened, {"status": "success"})
        return {"status": "connected"}
      except Exception as e:
        print(f'Exception Open Conn: {str(e)}')
        self.fire_event(CameraEvent.connection.failed, {"error": str(e)})
        return {"error": str(e), "status": "failed"}
        # self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    def stop(self, *args):
      print("Camera Stop", flush=True)
      self.connector.close()
      self.fire_event(CameraEvent.connection.closed, {"status": "success"})

    def close(self, *args):
      self.stop(args)


    def get_state(self, *args):
      print(f"get state {self.connector}", flush=True)
      print(f" the config = {self.config}", flush=True)
      running = False
      if self.connector and self.connector.alive and self.connector.video.isOpened():
        running = True
      return {"open": running, "running": running}

    def pause(self, *args):
      if self.state.recording:
        self.state.recording = "paused"
      return {"state": self.state}

    # def periodic(self, request_id, data):
    #   try:
    #     res = data.decode('utf-8')
    #     payload = json.loads(res)
    #     name = payload.get("name") or "PeriodicTask"
    #     method = payload.get("method")
    #     timeinterval = payload.get("interval")
    #     pt = PeriodicTask(name, request_id, payload)
    #     self.task_queue.put(pt)
    #     loop = IOLoop().current()
    #     loop.add_callback(self._process_tasks)

    #   except Exception as e:
    #     print(f"Cant periodic task {str(e)}", flush=True)


    # def stop_recording(self, request_id, data):
    #   try:
    #     res = data.decode('utf-8')
    #     payload = json.loads(res)
    #     name = payload.get("name") or "recording"
    #     if self.current_task[name]:
    #       self.current_task[name].cancel()
        
    #     self.state.status = 'Idle'
    #     self.state.recording = False
    #     return {"state": self.state}

    #     # # method = payload.get("method")
    #     # pt = CameraRecordTask(name, self, payload)
    #     # self.task_queue.put(pt)
    #     # loop = IOLoop().current()
    #     # loop.add_callback(partial(self._process_tasks))

    #   except Exception as e:
    #     print(f"Can't stop recording task {str(e)}", flush=True)

    #     return {"status": "failed", "reason": str(e)}

    def stop_recording(self, msg):
      print(f"STOP RECORDING {msg}", flush=True)      
      try:
        payload = msg.get('data')
        task_name = payload.get("task_name")
        cr = None
        if payload.get("recording_id"):
          cr = CameraRecording.get_by_id(payload.get("recording_id"))
          task_name = cr.task_name
        elif task_name:          
          cr = CameraRecording.select().where(CameraRecording.task_name == task_name).first()
        else:
          cr = CameraRecording.select().where(CameraRecording.status != "finished").first()
          if cr:
            task_name = cr.task_name

        for k, v in self.current_task.items():
            print(f"TASKkey = {k} and v = {v}", flush=True)

        if task_name:
          if self.current_task.get(task_name):
            self.current_task[task_name].cancel()
          else:
            if not cr.status.startswith("finished"):
              cr.status = "finished"
              cr.reason = "Cleanup No Task"
              cr.save()
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    def start_recording(self, msg):
      print(f"START RECORDING {msg}", flush=True)
      
      # return {"started": True}
      try:
        payload = msg.get('data')
    #     res = data.decode('utf-8')
    #     payload = json.loads(res)
        name = payload.get("print_id") or "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))
    #     # method = payload.get("method")

        pt = CameraRecordTask(name, self, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(partial(self._process_tasks))
        return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not record {str(e)}"}



    # def publish_request(self, request):
    #   rj = json.dumps(request.json).encode('ascii')
    #   self.pusher.send_multipart([self.identity+b'.request', b'request', rj])
            
              