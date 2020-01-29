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

import threading
import time
import zmq
import os
import shutil

import json
from tornado.ioloop import IOLoop

# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
from ...base_service import BaseService
from ....utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest
from .driver import CameraConnector
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream
import string, random


# from multiprocessing import Process, Lock, Pipe
# import multiprocessing as mp

# from ..tasks.device_task import PeriodicTask
# from ...tasks.camera_record_task import CameraRecordTask
# from ...tasks.camera_process_video_task import CameraProcessVideoTask

from ...events.camera import Camera as CameraEvent
from ...events.event_pack import EventPack
from ...middleware.camera_handler import CameraHandler
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError
from ...request import Request

from ...service_connector import ServiceConnector
from .camera_handler import CameraHandler as ProcessCameraHandler



global SEQ_ID
SEQ_ID = 0

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
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]

    def __init__(self, model, **kwargs):
        # self.camera_model = CameraModel.get(CameraModel.name == name)
        self.camera_model = CameraModel.get(CameraModel.service == model)
        # self.task_queue = Queue()
        # self.port = self.record['port']
        # self.baud_rate = self.record['baud_rate']

        
        super().__init__(model, **kwargs)        
        self.api = CameraApi(self)

        # self.camera_handler = CameraHandler(self)
        # self.register_data_handlers(self.camera_handler)
        
        # self.connector = None
        # self.video_processor = None

        self.event_class = CameraEvent

        self.state.load_dict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "recording": False
        })

        print(f'curpid = {os.getpid()} CurIOLOOP = {IOLoop.current()}', flush=True)        
        self.connector = None
        
        # # self.process = ServiceProcess(self.identity)
        # # self.process.daemon = True
        # self.process.start()

        # # self.statesub = self.ctx.socket(zmq.SUB)
        # # self.statesub.setsockopt_string(zmq.SUBSCRIBE, u'')
        # # self.statesub.connect(remote)

        # # # wrap statesub in ZMQStream for event triggers
        # # self.statesub = ZMQStream(self.statesub, self.loop)

        # # # setup basic reactor events
        # # self.heartbeat = PeriodicCallback(self.send_state,
        # #                                   HEARTBEAT, self.loop)
        # # self.statesub.on_recv(self.recv_state)

        # # self.ctx = zmq.Context.instance()
        # # self.bind_address = "tcp://*:5556"
        # # self.router_address = "tcp://127.0.0.1:5556"

        # cam_router = self.ctx.socket(zmq.ROUTER)
        # # zrouter.identity = self.identity
        # print(f'PRocess is alive = {self.process.is_alive()}', flush=True)
        # waitcnt = 10
        # while waitcnt > 0 and not self.process.is_alive():
        #   time.sleep(1)
        #   waitcnt -= 1
        # time.sleep(1)
        # router_address = self.process.get_router_address()
        # print(f"RouterAddress = {router_address}")
        # cam_router.connect(router_address)

        # self.cam_router = ZMQStream(cam_router)
        # self.cam_router.on_recv(self.router_message)
        # # self.cam_router.on_send(self.router_message_sent)

        # print(f'CamRouter = {self.cam_router}', flush=True)

        # self.pubsub_address = self.process.get_pubsub_address()
        # process_event_stream = self.ctx.socket(zmq.SUB)
        # process_event_stream.connect(self.pubsub_address)
        # self.process_event_stream = ZMQStream(process_event_stream)
        # self.process_event_stream.linger = 0
        # self.process_event_stream.on_recv(self.on_process_message)

        # self.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'events')

        # self.requests = {}

        # print(f"INSIDE base service {self.identity}", flush=True)
        # deid = f"inproc://{self.identity}_collector"
        # self.data_stream = self.ctx.socket(zmq.PULL)
        # # print(f'BEFORE CONNECT COLLECTOR NAME = {deid}', flush=True)  
        # self.data_stream.bind(deid)
        # # time.sleep(0.1)        
        # self.data_stream = ZMQStream(self.data_stream)
        # self.data_stream.linger = 0
        # self.data_stream.on_recv(self.on_data)
        # # self.data_stream.stop_on_recv()

        # event_stream = self.ctx.socket(zmq.SUB)
        # event_stream.connect("ipc://publisher")
        # self.event_stream = ZMQStream(event_stream)
        # self.event_stream.linger = 0
        # self.event_stream.on_recv(self.on_message)


        # ctx = mp.get_context('spawn')
        # self.rcp, child_conn = ctx.Pipe()
        # self.p = ctx.Process(target=run_camera, args=(self.identity, child_conn,))
        # self.p.daemon = True
        # self.p.start()
        # self.register_data_handlers(PrinterHandler(self))

    # def actions(self):
    #   return [
    #     "record"
    #   ]
    
    # def router_message_sent(self, msg, status):
    #   print(f"INSIDE CAM ROUTE SEND {msg} {status}", flush=True)

    # def setup_queue(self):
    #   print(f"Setup Queues {self}")
    #   ctx = zmq.Context()
    #   cam_router = ctx.socket(zmq.ROUTER)
    #   # zrouter.identity = self.identity
    #   print(f'PRocess is alive = {self.process.is_alive()}', flush=True)
    #   waitcnt = 10
    #   while waitcnt > 0 and not self.process.is_alive():
    #     time.sleep(1)
    #     waitcnt -= 1
    #   time.sleep(1)
    #   router_address = self.process.get_router_address()
    #   print(f"RouterAddress = {router_address}")
    #   cam_router.connect(router_address)

    #   self.cam_router = ZMQStream(cam_router)
    #   self.cam_router.on_recv(self.router_message)
    #   # self.cam_router.on_send(self.router_message_sent)

    #   print(f'CamRouter = {self.cam_router}', flush=True)

    #   self.pubsub_address = self.process.get_pubsub_address()
    #   process_event_stream = ctx.socket(zmq.SUB)
    #   process_event_stream.connect(self.pubsub_address)
    #   self.process_event_stream = ZMQStream(process_event_stream)
    #   self.process_event_stream.linger = 0
    #   self.process_event_stream.on_recv(self.on_process_message)

    #   self.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'events')

    #   self.requests = {}

    # def router_message(self, msg):
    #   # print("INSIDE CAM ROUTE message", flush=True)
    #   print(f"Cam Router Msg = {msg}", flush=True)
    #   ident, seq, payload = msg
    #   if seq in self.requests:
    #     self.requests[seq].set_result(payload)

    # def on_process_message(self, msg):
    #   print(f"CAM PUBSUB Msg = {msg}", flush=True)
    #   self.pusher.send_multipart(msg)


    def cleanup(self):
      print("cleanup camera", flush=True)
      if self.connector:
        self.connector.stop()
      # if self.connector:
      #   self.connector.close()
      # if self.video_processor:
      #   print(f"Close video processor")
      #   self.video_processor.close()
      # for k, v in self.current_task.items():
      #   if hasattr(v, "stop"):
      #       v.stop()
      print(f'Cleanup Process Stop', flush=True)
      super().cleanup()


    async def make_request(self, request):
      return await self.connector.make_request(request)

      # global SEQ_ID
      # SEQ_ID += 1
      # seq_s = struct.pack('!q', SEQ_ID)
      
      # loop = asyncio.get_running_loop()

      # # Create a new Future object.
      # fut = loop.create_future()
      # self.requests[seq_s] = fut
      # renc = request.encode()
      # print(f'Encode request = {renc}')
      # self.cam_router.send_multipart([self.identity, seq_s, renc])
      # # self.cam_router.send_multipart([self.identity, seq_s, json.dumps(request).encode('ascii')])

      # res = await fut
      # try:
      #   del self.requests[seq_s]
      #   res = json.loads(res.decode('utf-8'))
      #   classname = res.get('__class__')
      #   # print(f'classname = {classname}')
      #   module_name, class_name = classname.rsplit(".", 1)
      #   MyClass = getattr(importlib.import_module(module_name), class_name)
      #   if hasattr(MyClass, "decode"):
      #     res = MyClass.decode(res.get('data', {}))
      #   else:
      #     res = MyClass(res.get('data', {}))
        
      # except Exception as e:
      #   print('Exception')
      #   raise AncillaError(400, str(e))
      
      # if isinstance(res, AncillaError):
      #     raise res
      # return res


    def start(self, *args):
      print(f"START Camera {self.identity} {self.model.model.endpoint}", flush=True)
      # self.cam_router.send_multipart([b'start', self.model.model.endpoint.encode('ascii')])
      if not self.connector:
        self.connector = ServiceConnector(self, ProcessCameraHandler)
      self.connector.start()
      # self.setup_queue()
      # self.connector = CameraConnector(self.ctx, self.identity, self.model.model.endpoint)
      # self.connector.start()
    
    async def connect(self, *args):
      print("cam connect", flush=True)
      if not self.connector or not self.connector.is_alive():
        self.start()

      request = Request({"action": "connect", "body": {"endpoint": self.model.model.endpoint}})
      try:
        res =  await self.make_request(request)
        print(f'res = {res}')
        self.state.connected = True
        return res
      except Exception as e:   
        print(f"connect Exception =  {str(e)}")
        # await self.close()
        self.connector.stop()
        self.connector = None
        raise e

      return res



    async def stop(self, *args):
      print("Camera Stop", flush=True)
      if self.connector:
        self.connector.stop()
        self.connector = None
      # # request = {"action": "stop", "body": {}}
      # request = Request({"action": "stop", "body": {}})
      # res =  await self.make_request(request)
      # print(f'Stop res = {res}')
      self.state.connected = False
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
        # print(f'printStateChangeData= {data}', flush=True)
        # model = data.get("model")
        # print(f'printStateModel= {model}', flush=True)
        # name = model.get("name")
        # print(f'printStateModelName= {name}', flush=True)
        if data.get("status") in ["cancelled", "finished", "failed"]:
          self.stop_recording({"data": {}})
          # {"task_name": data.get("name")}

        return {"status": "success"}
        # else:
        #   return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant change recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not resume task {str(e)}"}

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
      # print(f"STOPRECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      try:
        print("video process record", flush=True)
        request = Request({"action": "stop_recording", "body": msg})
        res =  await self.make_request(request)
        print(f'stopviderecord = {res}')
        self.state.recording = False
        return res

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}


    async def start_recording(self, msg):
      # print(f"START RECORDING {msg}", flush=True)
      # print(f"RECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
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

        # payload = msg.get('data')
        payload.update({'camera_model': self.camera_model.to_json()})
        # msg.update({'data': payload})
        # msg.update({'camera_model': self.camera_model.to_json()})
      
        print("video process record", flush=True)
        # request = {"action": "start_recording", "body": msg}
        request = Request({"action": "start_recording", "body": {'data': payload}})
        res =  await self.make_request(request)
        print(f'getviderecord = {res}')
        self.state.recording = True
        return res
 

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not record {str(e)}"}


    async def get_or_create_video_processor(self):
      if not self.state.connected:
        raise AncillaError(400, {"error": "Camera Not Connected"})
      
      print("video process connect", flush=True)
      # request = {"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}}
      request = Request({"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}})
      res =  await self.make_request(request)
      return res


