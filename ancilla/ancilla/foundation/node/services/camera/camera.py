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


from multiprocessing import Process, Lock, Pipe
import multiprocessing as mp

# from ..tasks.device_task import PeriodicTask
from ...tasks.camera_record_task import CameraRecordTask
from ...tasks.camera_process_video_task import CameraProcessVideoTask

from ...events.camera import Camera as CameraEvent
from ...events.event_pack import EventPack
from ...middleware.camera_handler import CameraHandler
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError

from .service_process import ServiceProcess

def run_camera(identity, conn):

  pass

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

        self.camera_handler = CameraHandler(self)
        self.register_data_handlers(self.camera_handler)
        
        self.connector = None
        self.video_processor = None

        self.event_class = CameraEvent

        self.state.load_dict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "recording": False
        })

        print(f'curpid = {os.getpid()} CurIOLOOP = {IOLoop.current()}', flush=True)        
        self.process = ServiceProcess(self.identity)
        # self.process.daemon = True
        self.process.start()

        # self.statesub = self.ctx.socket(zmq.SUB)
        # self.statesub.setsockopt_string(zmq.SUBSCRIBE, u'')
        # self.statesub.connect(remote)

        # # wrap statesub in ZMQStream for event triggers
        # self.statesub = ZMQStream(self.statesub, self.loop)

        # # setup basic reactor events
        # self.heartbeat = PeriodicCallback(self.send_state,
        #                                   HEARTBEAT, self.loop)
        # self.statesub.on_recv(self.recv_state)




        # self.ctx = zmq.Context.instance()
        # self.bind_address = "tcp://*:5556"
        # self.router_address = "tcp://127.0.0.1:5556"

        cam_router = self.ctx.socket(zmq.ROUTER)
        # zrouter.identity = self.identity
        print(f'PRocess is alive = {self.process.is_alive()}', flush=True)
        waitcnt = 10
        while waitcnt > 0 and not self.process.is_alive():
          time.sleep(1)
          waitcnt -= 1
        time.sleep(1)
        router_address = self.process.get_router_address()
        print(f"RouterAddress = {router_address}")
        cam_router.connect(router_address)

        self.cam_router = ZMQStream(cam_router)
        self.cam_router.on_recv(self.router_message)
        self.cam_router.on_send(self.router_message_sent)

        print(f'CamRouter = {self.cam_router}', flush=True)

        self.pubsub_address = self.process.get_pubsub_address()
        event_stream = self.ctx.socket(zmq.SUB)
        event_stream.connect(self.pubsub_address)
        self.event_stream = ZMQStream(event_stream)
        self.event_stream.linger = 0
        self.event_stream.on_recv(self.on_message)

        self.requests = {}

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
    
    def router_message_sent(self, msg, status):
      print(f"INSIDE CAM ROUTE SEND {msg} {status}", flush=True)

    def router_message(self, msg):
      print("INSIDE CAM ROUTE message", flush=True)
      print(f"Router Msg = {msg}", flush=True)
      ident, seq, payload = msg
      if seq in self.requests:
        self.requests[seq].set_result(payload)

    def on_message(self, msg):
      print(f"CAM PUBSUB Msg = {msg}", flush=True)

    def cleanup(self):
      print("cleanup camera", flush=True)
      if self.connector:
        self.connector.close()
      if self.video_processor:
        print(f"Close video processor")
        self.video_processor.close()
      for k, v in self.current_task.items():
        if hasattr(v, "stop"):
            v.stop()
      super().cleanup()

    # def send_request(self, request):
    #   seq_s = struct.pack('!q', SEQ_ID)
      

    # async def set_after(fut, delay, value):
    #   # Sleep for *delay* seconds.
    #   await asyncio.sleep(delay)

    #   # Set *value* as a result of *fut* Future.
    #   fut.set_result(value)


    async def make_request(self, request):
      global SEQ_ID
      SEQ_ID += 1
      seq_s = struct.pack('!q', SEQ_ID)
      
      loop = asyncio.get_running_loop()

      # Create a new Future object.
      fut = loop.create_future()
      self.requests[seq_s] = fut
      
      self.cam_router.send_multipart([self.identity, seq_s, json.dumps(request).encode('ascii')])

      res = await fut
      del self.requests[seq_s]
      return res
      # task = asyncio.create_task(coro())
      # future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
      #   print("FUTURE = ", future)
      #   zmqrouter = self.zmq_router
      #   def onfinish(fut):
      #     newres = fut.result(1)
      #     status = b'success'
      #     if "error" in newres:
      #       status = b'error'
      #     zmqrouter.send_multipart([replyto, status, json.dumps(newres).encode('ascii')])

      #   future.add_done_callback(onfinish)
      # pass

    def start(self, *args):
      print(f"START Camera {self.identity} {self.model.model.endpoint}", flush=True)
      self.cam_router.send_multipart([b'start', self.model.model.endpoint.encode('ascii')])
      # self.connector = CameraConnector(self.ctx, self.identity, self.model.model.endpoint)
      # self.connector.start()
    
    async def connect(self, *args):
      print("cam connect", flush=True)
      print(f'cam rec= {CameraRecording._meta.database.__dict__}')
      request = {"action": "connect", "body": {"endpoint": self.model.model.endpoint}}
      res =  await self.make_request(request)
      print(f'res = {res}')
      self.state.connected = True
      return res

      
      
      # self.cam_router.send_multipart([self.identity, b'connect', self.model.model.endpoint.encode('ascii')])
      
      # return {"status": "connected"}
      # try:
      #   if not self.connector:
      #     self.start()
      #   #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
      #   # else:
      #   self.connector.open()
      #   print("Camera Connect", flush=True)
      #   self.connector.run()
      #   self.state.connected = True
      #   self.fire_event(CameraEvent.connection.opened, {"status": "success"})
      #   return {"status": "connected"}
      # except Exception as e:
      #   print(f'Exception Open Conn: {str(e)}')
      #   self.state.connected = False
      #   self.fire_event(CameraEvent.connection.failed, {"error": str(e)})
      #   raise AncillaError(400, {"error": str(e)})
        # return {"error": str(e), "status": "failed"}
        # self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    async def stop(self, *args):
      print("Camera Stop", flush=True)
      request = {"action": "stop", "body": {}}
      res =  await self.make_request(request)
      print(f'Stop res = {res}')
      self.state.connected = False
      return res

      # self.connector.close()
      # self.connector = None
      # self.state.connected = False
      # self.fire_event(CameraEvent.connection.closed, {"status": "success"})

    def close(self, *args):
      self.stop(args)


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

    def resume_recording(self, msg):
      try:
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.resume()
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant resume recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not resume task {str(e)}"}

    def pause_recording(self, msg):
      try:
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.pause()
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant pause recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not pause task {str(e)}"}

    async def stop_recording(self, msg):
      # print(f"STOP RECORDING {msg}", flush=True)      
      # print(f"STOPRECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      try:
        print("video process record", flush=True)
        request = {"action": "stop_recording", "body": msg}
        res =  await self.make_request(request)
        print(f'stopviderecord = {res}')
        try:
          res = json.loads(res.decode('utf-8'))
          self.state.recording = False
        except Exception as e:
          print(f"cant load json {str(e)}")
        # self.state.connected = True
        return res

        # payload = msg.get('data')
        # task = self.get_recording_task(payload)
        # if task:
        #   task.cancel()
        #   return {"status": "success"}
        # else:
        #   return {"status": "error", "error": "Task Not Found"}

        

        # task_name = payload.get("task_name")
        # cr = None
        # if payload.get("recording_id"):
        #   cr = CameraRecording.get_by_id(payload.get("recording_id"))
        #   task_name = cr.task_name
        # # elif task_name:          
        # #   cr = CameraRecording.select().where(CameraRecording.task_name == task_name).first()
        # # else:
        # #   cr = CameraRecording.select().where(CameraRecording.status != "finished").first()
        # #   if cr:
        # #     task_name = cr.task_name

        # for k, v in self.current_task.items():
        #     print(f"TASKkey = {k} and v = {v}", flush=True)

        # if task_name:
        #   if self.current_task.get(task_name):
        #     self.current_task[task_name].cancel()
        #   else:
        #     if not cr.status.startswith("finished"):
        #       cr.status = "finished"
        #       cr.reason = "Cleanup No Task"
        #       cr.save()
        #   return {"status": "success"}
        # else:
        #   return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    def get_recording_task(self, data):
      # print(f"Get RECORDING {data}", flush=True)    
      # print(f"GET RECORDINGData: {json.dumps(data, cls=ServiceJsonEncoder)}", flush=True)  
      try:
        
        task_name = data.get("task_name")
        cr = None
        if data.get("recording_id"):
          cr = CameraRecording.get_by_id(data.get("recording_id"))
          task_name = cr.task_name

        printmodel = data.get("model")
        
        # elif task_name:          
        #   cr = CameraRecording.select().where(CameraRecording.task_name == task_name).first()
        # else:
        #   cr = CameraRecording.select().where(CameraRecording.status != "finished").first()
        #   if cr:
        #     task_name = cr.task_name

        for k, v in self.current_task.items():
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

        # if task_name:
        #   if self.current_task.get(task_name):
        #     self.current_task[task_name].cancel()
        #   else:
        #     if not cr.status.startswith("finished"):
        #       cr.status = "finished"
        #       cr.reason = "Cleanup No Task"
        #       cr.save()
        #   return {"status": "success"}
        # else:
        #   return {"status": "error", "error": "Task Not Found"}

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}



    async def start_recording(self, msg):
      # print(f"START RECORDING {msg}", flush=True)
      # print(f"RECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      # return {"started": True}
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
          self.connect()

        # payload = msg.get('data')
        payload.update({'camera_model': self.camera_model.to_json()})
        msg.update({'data': payload})
        # msg.update({'camera_model': self.camera_model.to_json()})
      
        print("video process record", flush=True)
        request = {"action": "start_recording", "body": msg}
        res =  await self.make_request(request)
        print(f'getviderecord = {res}')
        try:
          res = json.loads(res.decode('utf-8'))
          self.state.recording = True
        except Exception as e:
          print(f"cant load json {str(e)}")
        # self.state.connected = True
        return res
        

        # name = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))

        
        # pt = CameraRecordTask(name, self, payload)
        # self.task_queue.put(pt)
        # loop = IOLoop().current()
        # loop.add_callback(partial(self._process_tasks))
        # return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not record {str(e)}"}


    async def get_or_create_video_processor(self):
      if not self.state.connected:
        raise AncillaError(400, {"error": "Camera Not Connected"})
      
      print("video process connect", flush=True)
      request = {"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}}
      res =  await self.make_request(request)
      print(f'getvideres = {res}')
      try:
        res = json.loads(res.decode('utf-8'))
        
      except Exception as e:
        print(f"cant load json {str(e)}")
      # self.state.connected = True
      return res


      # if self.video_processor:
      #     for k, v in self.current_task.items():
      #       if isinstance(v, CameraProcessVideoTask):              
      #         return v


      # payload = {"settings": {}}
      # self.video_processor = CameraProcessVideoTask("process_video", self, payload)
      # self.task_queue.put(self.video_processor)
      # loop = IOLoop().current()
      # loop.add_callback(partial(self._process_tasks))
      # return self.video_processor


    # def delete_recording(self, msg):
    #   if isinstance(msg, CameraRecording):
    #     recording = msg
    #   else:
    #     data = msg.get("data") or None
    #     if data:
    #       if data.get("id"):
    #         recording = CameraRecording.get_by_id(data.get("id"))     
      
    #   if recording:
    #     try:
          
    #       if os.path.exists(recording.image_path):
    #         shutil.rmtree(recording.image_path)
    #       if os.path.exists(recording.video_path):
    #         shutil.rmtree(recording.video_path)

    #       res = recording.delete_instance(recursive=True)
    #       self.fire_event(CameraEvent.recording.deleted, {"data": recording.json})
    #       return True
    #     except Exception as e:
    #       print(f"delete exception {str(e)}")
    #       raise e
      
    #   return False


    # def publish_request(self, request):
    #   rj = json.dumps(request.json).encode('ascii')
    #   self.pusher.send_multipart([self.identity+b'.request', b'request', rj])
            
              
