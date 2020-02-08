'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import logging
import time
import os
import json
import string, random

from ....data.models import Camera as CameraModel, CameraRecording

from .driver import CameraConnector

from ...tasks.camera_record_task import CameraRecordTask
from ...tasks.camera_process_video_task import CameraProcessVideoTask

from ...events.camera import Camera as CameraEvent
from ...middleware.camera_handler import CameraHandler as CameraDataHandler
from ...response import AncillaResponse, AncillaError
from ...request import Request

from ....utils.delegate import DelegatedAttribute

class CameraHandler():
    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]
    connector = None
    video_processor = None


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
      if self.connector and self.connector.alive:
        return {"status": "connected"}

      self.connector = CameraConnector(self.process.ctx, self.process.identity, endpoint)
      self.connector.open()
      
      self.connector.run()
      self.state.connected = True

      self.process.fire_event(CameraEvent.connection.opened, self.state)
      return {"status": "connected"}


    def get_or_create_video_processor(self, *args):
      # if not self.state.connected:
      #   raise AncillaError(400, {"error": "Camera Not Connected"})
      
      if self.video_processor:
          for k, v in self.process.current_tasks.items():
            if isinstance(v, CameraProcessVideoTask):    
              return {"stream": v.processed_stream}
              # return v

      payload = {"settings": {}}
      self.video_processor = CameraProcessVideoTask("process_video", self.process, payload)
      self.process.add_task(self.video_processor)

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
          # print(f"TASKkey = {k} and v = {v}", flush=True)
          if isinstance(v, CameraRecordTask):
            if printmodel:
              if v.recording.print_id == printmodel.get("id"):
                return v
            if task_name:
              if k == task_name:
                return v
            else:
              return v
        return None

      except Exception as e:
        print(f"Cant get recording task {str(e)}", flush=True)
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
      try:

        payload = msg.get('data')
        name = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))

        pt = CameraRecordTask(name, self.process, payload)
        self.process.add_task(pt)
        self.state.recording = True

        return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        raise AncillaError(400, {"status": "error", "error": f"Could not record {str(e)}"}, exception=e)
        # return {"status": "error", "error": f"Could not record {str(e)}"}

    




