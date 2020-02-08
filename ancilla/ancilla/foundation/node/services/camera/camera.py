'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import logging
import time
import os
import shutil

import json

from ....data.models import Camera as CameraModel, CameraRecording
from ...base_service import BaseService

from ...events.camera import Camera as CameraEvent
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError
from ...request import Request

from ...service_connector import ServiceConnector
from .camera_handler import CameraHandler as ProcessCameraHandler


class Camera(BaseService):
    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]

    def __init__(self, model, **kwargs):
        self.camera_model = CameraModel.select().where(CameraModel.service == model).first()

        super().__init__(model, **kwargs)        
        self.api = CameraApi(self)


        self.event_class = CameraEvent
        self.intial_state = {
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "recording": False
        }

        self.state.load_dict(self.intial_state)

        self.connector = None


    def cleanup(self):
      print("cleanup camera", flush=True)
      if self.connector:
        self.connector.stop()
      super().cleanup()


    def update_model(self, service_model):
      self.camera_model = service_model.model
      super().update_model(service_model)

    async def make_request(self, request):
      if self.connector:
        return await self.connector.make_request(request)
      else:
        self.state.connected = False
      raise AncillaError(400, {"error": "Not Connected"})


    def start(self, *args):
      print(f"START Camera {self.identity} {self.model.model.endpoint}", flush=True)
      if not self.connector:
        self.connector = ServiceConnector(self, ProcessCameraHandler)
      self.connector.start()

    
    async def connect(self, *args):
      print("cam connect", flush=True)
      if not self.connector or not self.connector.is_alive():
        self.start()

      request = Request({"action": "connect", "body": {"endpoint": self.model.model.endpoint}})
      try:
        res =  await self.make_request(request)
        self.state.connected = True
        return res
      except Exception as e:   
        print(f"connect Exception =  {str(e)}")
        self.connector.stop()
        self.connector = None
        raise e

      return res



    async def stop(self, *args):
      print("Camera Stop", flush=True)
      if self.connector:
        self.connector.stop()
        self.connector = None

      self.state.load_dict(self.intial_state)
      self.fire_event(self.event_class.state.changed, self.state)

      return {"success": True }

    async def close(self, *args):
      await self.stop(args)

    # def get_state(self, *args):
    #   print(f"get state {self.connector}", flush=True)
    #   print(f" the config = {self.config}", flush=True)
    #   running = False
    #   if self.connector and self.connector.alive and self.connector.video.isOpened():
    #     running = True
    #   return {"open": running, "running": running}

    def pause(self, *args):
      if self.state.recording:
        self.state.recording = "paused"
      return {"state": self.state}


    def print_state_change(self, msg):
      try:
        name = msg.get('name')
        data = msg.get('data')

        if data.get("status") in ["cancelled", "finished", "failed"]:
          self.stop_recording({"data": {}})
          # {"task_name": data.get("name")}

        return {"status": "success"}
        # else:
        #   return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant change recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not resume task {str(e)}"}

    def delete_recording(self, msg):
      rid = msg.get("data", {}).get("id")
      if rid:
        recording = CameraRecording.get_by_id(rid)

      if recording:
        try:
          
          if os.path.exists(recording.image_path):
            shutil.rmtree(recording.image_path)
          if os.path.exists(recording.video_path):
            shutil.rmtree(recording.video_path)

          res = recording.delete_instance()
          return {"success": True}
        except Exception as e:
          print(f"delete recording exception {str(e)}")
          raise AncillaError(400, {"status": "error", "error": f"Could not delete recording {str(e)}"}, exception=e)
      
      raise AncillaError(400, {"status": "error", "error": f"Could not delete recording"})


    # async def delete_recording(self, msg):
    #   try:
    #     request = Request({"action": "delete_recording", "body": msg})
    #     res =  await self.make_request(request)
    #     return res
    #   except Exception as e:
    #     print(f"Cant delete recording {str(e)}", flush=True)
    #     return {"status": "error", "error": f"Could not delete recording {str(e)}"}

    async def resume_recording(self, msg):
      try:
        request = Request({"action": "resume_recording", "body": msg})
        res =  await self.make_request(request)
        return res
      except Exception as e:
        print(f"Cant resume recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not resume task {str(e)}"}

    async def pause_recording(self, msg):
      try:
        request = Request({"action": "pause_recording", "body": msg})
        res =  await self.make_request(request)
        return res
      except Exception as e:
        print(f"Cant pause recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not pause task {str(e)}"}

    async def stop_recording(self, msg):
      # print(f"STOP RECORDING {msg}", flush=True)
      try:
        request = Request({"action": "stop_recording", "body": msg})
        res =  await self.make_request(request)
        self.state.recording = False
        return res

      except Exception as e:
        print(f"Cant stop recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}


    async def start_recording(self, msg):
      # print(f"START RECORDING {msg}", flush=True)
      try:

        payload = msg.get('data')
        printmodel = payload.get("model")
        if printmodel:
          record_print = False
          settings = printmodel.get("settings") or {}
          if settings.get("record_print") == True:
            if f'{self.model.id}' in (settings.get("cameras") or {}).keys():
              record_print = True
          
          if not record_print:
            return {"status": "ok", "reason": "Dont record this print"}

        if not self.state.connected:
          await self.connect()

        payload.update({'camera_model': self.camera_model.to_json()})

        request = Request({"action": "start_recording", "body": {'data': payload}})
        res =  await self.make_request(request)
        self.state.recording = True
        return res
 

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not record {str(e)}"}


    async def get_or_create_video_processor(self):
      if not self.state.connected:
        raise AncillaError(400, {"error": "Camera Not Connected"})
      
      # request = {"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}}
      request = Request({"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}})
      res =  await self.make_request(request)
      return res


