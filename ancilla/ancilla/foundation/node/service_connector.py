'''
 service_connector.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/26/20
 Copyright 2019 FrenzyLabs, LLC.
'''



import logging
import sys
import time
import zmq
import importlib

import os

import json


# from ..zhelpers import zpipe, socket_set_hwm
# from ....data.models import Camera as CameraModel, CameraRecording
from .base_service import BaseService
from ..utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest
# from .driver import CameraConnector
# from queue import Queue
# import asyncio



# from tornado.gen        import coroutine, sleep
# from collections import OrderedDict
import struct # for packing integers
# from zmq.eventloop.ioloop import PeriodicCallback

# from zmq.asyncio import Context, ZMQEventLoop

from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop, PeriodicCallback

import inspect
import asyncio
from types import CoroutineType

# from tornado.platform.asyncio import AnyThreadEventLoopPolicy


# from ..tasks.device_task import PeriodicTask
# from ...tasks.camera_record_task import CameraRecordTask
# from ...tasks.camera_process_video_task import CameraProcessVideoTask

# from ...events import Event, EventPack
# from ...events.camera import Camera as CameraEvent
# from ...events.event_pack import EventPack
# from ...middleware.camera_handler import CameraHandler
# from ...api.camera import CameraApi
from .response import AncillaResponse, AncillaError
from .request import Request
# from .app import App, ConfigDict

from multiprocessing import Process, Lock, Pipe
import multiprocessing as mp



# from .camera_process import CameraProcess
from .service_process import ServiceProcess


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


global SEQ_ID
SEQ_ID = 0


class ServiceConnector():
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

    def __init__(self, service, handler, **kwargs): 
        ctx = mp.get_context('spawn')
        # ctx.set_start_method('spawn')
        # ctx.Process.__init__(self)
        # super().__init__(**kwargs)
        self.service = service
        self.identity = service.identity
        
        self.loop = None
        print(f"PROCESS ID + {os.getpid()}", flush=True)
        
        self.router_address = None
        self.rpc_router = None
        self.process_event_stream = None
        self.requests = {}
        self.ctx = zmq.Context()
        
        self.rpc, self.child_conn = Pipe()
        # self.p = ctx.Process(target=CameraProcess.start_process, args=(self.identity, self.child_conn,))
        self.p = ctx.Process(target=ServiceProcess.start_process, args=(self.identity, self.child_conn, handler))
        
        # self.parent_conn, child_conn = ctx.Pipe()
        # self.p = ctx.Process(target=self.run, args=(self.child_conn,))
        # self.p.daemon = True
        
        
        # self.router_address = None
        # asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        
        # self.ctx = zmq.Context.instance()
        # self.port = 5556
        

        
        
        

        # self.camera_handler = CameraHandler(self)
        # self.register_data_handlers(self.camera_handler)
        # self.api = CameraApi(self)
        # self.connector = None
        # self.video_processor = None

        # self.event_class = CameraEvent

        # self.state.load_dict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "recording": False
        # })

        # self.register_data_handlers(PrinterHandler(self))

    # def actions(self):
    #   return [
    #     "record"
    #   ]
    def start(self, *args):
      print(f'Start Process {self.p}')
      self.p.start()
      print(f'STARTING PROCESS')
      self.setup_queue()

    def stop(self, *args):
      print(f'Stop Process 1')
      self.rpc.send(("stop", ""))  
      print(f'Stop Process After Send')
      cnt = 10
      while cnt > 0:
        res = self.rpc.poll(1)
        if res:
          print(f"res = {res} {cnt}")
          tada = self.rpc.recv()
          break 

        cnt -= 1
      
      

      self.p.join(2)
      # self.p.terminate()
      self.p = None
      print(f'Stopped Process')
      self.rpc_router.close()
      # self.process_event_stream.close()
      
      # self.ctx.destroy()
      
    def setup_queue(self):
      print(f"Setup Queues {self}")
      
      rpc_router = self.ctx.socket(zmq.ROUTER)
      # zrouter.identity = self.identity
      print(f'PRocess is alive = {self.is_alive()}', flush=True)
      waitcnt = 100
      while waitcnt > 0 and not self.is_alive():
        time.sleep(0.1)
        waitcnt -= 1
      time.sleep(0.5)
      router_address = self.get_router_address()
      print(f"RouterAddress = {router_address}")
      rpc_router.connect(router_address)

      self.rpc_router = ZMQStream(rpc_router)
      self.rpc_router.on_recv(self.router_message)
      # self.cam_router.on_send(self.router_message_sent)

      print(f'CamRouter = {self.rpc_router}', flush=True)

      self.pubsub_address = self.get_pubsub_address()
      process_event_stream = self.ctx.socket(zmq.SUB)
      process_event_stream.connect(self.pubsub_address)
      self.process_event_stream = ZMQStream(process_event_stream)
      self.process_event_stream.linger = 0
      self.process_event_stream.on_recv(self.on_process_message)

      self.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'events')

      # self.requests = {}

    def is_alive(self, *args):
      return (self.p and self.p.is_alive())
      
    def get_router_address(self):
      self.rpc.send(("router_address", ""))
      (key, val) = self.rpc.recv()
      self.router_address = val
      return self.router_address

    def get_pubsub_address(self):
      self.rpc.send(("pubsub_address", ""))
      (key, val) = self.rpc.recv()
      self.pubsub_address = val
      return self.pubsub_address
      
    def on_process_message(self, msg):
      # print(f"CAM PUBSUB Msg = {msg}", flush=True)
      self.service.pusher.send_multipart(msg)

    def router_message(self, msg):
      # print("INSIDE CAM ROUTE message", flush=True)
      print(f"Cam Router Msg = {msg}", flush=True)
      ident, seq, payload = msg
      if seq in self.requests:
        self.requests[seq].set_result(payload)


    async def make_request(self, request):
      global SEQ_ID
      SEQ_ID += 1
      seq_s = struct.pack('!q', SEQ_ID)
      
      loop = asyncio.get_running_loop()

      # Create a new Future object.
      fut = loop.create_future()
      self.requests[seq_s] = fut
      renc = request.encode()
      print(f'Encode request = {renc}')
      self.rpc_router.send_multipart([self.identity, seq_s, renc])
      # self.cam_router.send_multipart([self.identity, seq_s, json.dumps(request).encode('ascii')])

      res = await fut
      try:
        del self.requests[seq_s]
        res = json.loads(res.decode('utf-8'))
        classname = res.get('__class__')
        # print(f'classname = {classname}')
        module_name, class_name = classname.rsplit(".", 1)
        MyClass = getattr(importlib.import_module(module_name), class_name)
        if hasattr(MyClass, "decode"):
          res = MyClass.decode(res.get('data', {}))
        else:
          res = MyClass(res.get('data', {}))
        
      except Exception as e:
        print('Exception')
        raise AncillaError(400, str(e))
      
      if isinstance(res, AncillaError):
          raise res
      return res

