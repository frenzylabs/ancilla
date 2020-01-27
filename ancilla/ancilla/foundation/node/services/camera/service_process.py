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


# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
from ...base_service import BaseService
from ....utils.service_json_encoder import ServiceJsonEncoder

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
from ...middleware.camera_handler import CameraHandler
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError


from multiprocessing import Process, Lock, Pipe, Value, Array
import multiprocessing as mp
from ctypes import c_char_p

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


class ServiceProcess(Process):
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

    def __init__(self, identity, **kwargs):        
        super().__init__(**kwargs)
        self.identity = identity
        # self.conn = conn
        self.loop = None
        print(f"PROCESS ID + {os.getpid()}", flush=True)
        self.rpc, self.child_conn = Pipe()
        self.router_address = None



        
        # self.router_address = None
        # asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        
        # self.ctx = zmq.Context.instance()
        # self.port = 5556
        

        # self.zrouter = self.ctx.socket(zmq.DEALER)
        # self.zrouter.identity = self.identity
        # trybind = 30
        # bound = False
        # while not bound and trybind > 0:
        #   try:
        #     self.bind_address = f"tcp://*:{self.port}"
        #     self.router_address = f"tcp://127.0.0.1:{self.port}"
        #     self.zrouter.bind(self.bind_address)
        #     print(f"Bound to {self.bind_address}")
        #     bound = True
        #   except zmq.error.ZMQError:
        #     trybind -= 1
        #     self.port += 1
        
        # if not bound:
        #   raise Exception("Could Not Bind To Address")
        
        
        

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
      
    # def run2(self):
    #     running = True
    #     # while running:
    #     print(f"RUN PROCESS ID + {os.getpid()}", flush=True)
    #     IOLoop.clear_current()
    #     if hasattr(IOLoop, '_current'):
    #       del IOLoop._current
        
    #     print(f"INSIDE PROCESS SERVICE RUN {IOLoop.current(instance=False)}", flush=True)

        
    #     print(f"PLOOP = {IOLoop.current()}", flush=True)
    #     if self.loop is None:
    #         if not IOLoop.current(instance=False):
    #             self.loop = IOLoop()
    #         else:
    #             self.loop = IOLoop.current()
    #     # self.loop = IOLoop().initialize(make_current=False)  
    #     # self.loop = IOLoop.current()
    #     print(f"INSIDE PROCESS LOOP= {self.loop}", flush=True)
    #     self.zmq_router = ZMQStream(self.zrouter) #, self.loop)
    #     self.zmq_router.on_recv(self.router_message)
    #     self.zmq_router.on_send(self.router_message_sent)
    #     # loop = IOLoop.current(instance=True)
    #     self.heartbeat = PeriodicCallback(self.send_state, 3000)        
    #     self.heartbeat.start()
        
    #     while True:
    #       future = asyncio.run_coroutine_threadsafe(asyncio.sleep(1), asyncio.get_running_loop())
    #       # await 
    #     try:
    #       self.loop.start()
          
    #       print("LOOP STARTED", flush=True)
    #     except KeyboardInterrupt:
    #         pass

    # def run_server():
    #   context = Context()
    #   server = context.socket(zmq.REP)
    #   server.bind(SERVER_ADDR)
    #   cycles = 0
    #   while True:
    #       request = yield from server.recv()
    #       cycles += 1
    #       # Simulate various problems, after a few cycles
    #       if cycles > 3 and randint(0, 3) == 0:
    #           print("I: Simulating a crash")
    #           server.unbind(SERVER_ADDR)
    #           # Delay for a bit, else we get "Address already in use" error.
    #           # Note that to really simulate a crash, we should probably kill
    #           # this process and start another.
    #           yield from asyncio.sleep(2)
    #           break
    #       elif cycles > 3 and randint(0, 3) == 0:
    #           print("I: Simulating CPU overload")
    #           yield from asyncio.sleep(2)
    #       print("I: Normal request (%s)" % request)
    #       yield from asyncio.sleep(1)       # Do some heavy work
    #       yield from server.send(request)
    #   return (context, server)

    def setup_router(self):
      self.zrouter = self.ctx.socket(zmq.ROUTER)
      self.zrouter.identity = self.identity
      trybind = 30
      bound = False
      while not bound and trybind > 0:
        try:
          self.bind_address = f"tcp://*:{self.port}"
          
          self.zrouter.bind(self.bind_address)
          self.router_address = f"tcp://127.0.0.1:{self.port}"
          print(f"Bound to {self.bind_address}")
          bound = True
        except zmq.error.ZMQError:
          trybind -= 1
          self.port += 1
      
      if not bound:
        raise Exception("Could Not Bind To Address")

    
    def setup_publiser(self):
      self.zpub = self.ctx.socket(zmq.PUB)
      trybind = 30
      bound = False
      while not bound and trybind > 0:
        try:
          self.pub_bind_address = f"tcp://*:{self.pub_port}"
          
          self.zpub.bind(self.pub_bind_address)
          self.pubsub_address = f"tcp://127.0.0.1:{self.pub_port}"
          print(f"Pub Bound to {self.pub_bind_address}")
          bound = True
        except zmq.error.ZMQError:
          trybind -= 1
          self.pub_port += 1
      
      if not bound:
        raise Exception("Could Not Bind To Address")


    def register_data_handlers(self, obj):
      self.data_handlers.append(obj)

    def setup_data(self):
        self.data_handlers = []        
        self.camera_handler = CameraHandler(self)
        self.register_data_handlers(self.camera_handler)

        print(f"INSIDE base service {self.identity}", flush=True)
        deid = f"inproc://{self.identity}_collector"
        self.data_stream = self.ctx.socket(zmq.PULL)
        # print(f'BEFORE CONNECT COLLECTOR NAME = {deid}', flush=True)  
        self.data_stream.bind(deid)
        # time.sleep(0.1)        
        self.data_stream = ZMQStream(self.data_stream)
        self.data_stream.linger = 0
        self.data_stream.on_recv(self.on_data)

    def setup(self):
      from ....env import Env
      from ....data.db import Database
      from playhouse.sqlite_ext import SqliteExtDatabase
      import zmq
      Env.setup()
      
      conn = SqliteExtDatabase(Database.path, pragmas=(
        # ('cache_size', -1024 * 64),  # 64MB page-cache.
        ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
        ('foreign_keys', 1),
        ('threadlocals', True)))
      Database.conn.close()
      Database.conn = conn
      Database.connect()
        # {'foreign_keys' : 1, 'threadlocals': True})
      # conn.connect()
      # # Database.connect()
      # # pr(lock, f'conn = {conn}')
      from ....data.models import Camera, CameraRecording, Print, PrintSlice, PrinterCommand
      # Camera._meta.database = conn
      CameraRecording._meta.database = conn
      print(f'SETUP PRC {CameraRecording._meta.database.__dict__}')
      
      # PrinterCommand._meta.database = conn


      self.task_queue = Queue()
      self.current_task = {}
      self.video_processor = None

    async def run_loop(self, loop, child_conn):
      
      IOLoop.clear_current()
      if hasattr(IOLoop, '_current'):
        del IOLoop._current
      
      print(f"INSIDE PROCESS SERVICE RUN {IOLoop.current(instance=False)}", flush=True)

      if self.loop is None:
          if not IOLoop.current(instance=False):
              self.loop = IOLoop.current() #IOLoop()
          else:
              self.loop = IOLoop.current()

      print(f"PLOOP = {self.loop}", flush=True)

      self.setup()

      self.ctx = zmq.Context.instance()
      self.port = 5556
      self.pub_port = 5557

      self.setup_router()
      self.zmq_router = ZMQStream(self.zrouter, self.loop)
      self.zmq_router.on_recv(self.router_message)
      # self.zmq_router.on_send(self.router_message_sent)


      self.setup_publiser()
      self.zmq_pub = ZMQStream(self.zpub, self.loop)
      # self.zmq_pub.on_recv(self.pub_message)
      

      self.setup_data()

      self.heartbeat = PeriodicCallback(self.send_state, 6000)        
      self.heartbeat.start()
      
      print(f"INSIDE run loop {self.loop}")
      # self.loop.start()
      # self.loop.run_forever()
      # print("AFTER LOOP")

      while self.running:
        res = self.child_conn.poll(0.01)
        if res:
          payload = self.child_conn.recv()
          if payload:
            (key, args) = payload
            if key == "router_address":
              self.child_conn.send((key, self.router_address))
            elif key == "pubsub_address":
              self.child_conn.send((key, self.pubsub_address))
        await asyncio.sleep(1)


    def run(self):
      # asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
      self.running = True
      try:
          # loop = ZMQEventLoop()
          evtloop = asyncio.new_event_loop()
          asyncio.set_event_loop(evtloop)
          # self.run_loop(evtloop)
          evtloop.run_until_complete(self.run_loop(evtloop, self.child_conn))
          print("RUN PROCESS COMPLETE")
      except KeyboardInterrupt:
        self.running = False
        print('\nFinished (interrupted)')
    
    
    def send_state(self, *a, **kw):
      print("SENDING STATE", flush=True)

    def on_message(self, msg):
      print("ON MESSGE", msg)      
      # if not msg or len(msg) < 3:
      #   return
      # topic, ident, pstring, *other = msg
      # topic = topic.decode('utf-8')
      # ident = ident.decode('utf-8')
      # data = pstring.decode('utf-8')
      # try:
      #   data = json.loads(data)
      # except Exception as e:
      #   print("NOt json")

      # epack = EventPack(topic, ident, data)

      # # el = self.settings.get("event_handlers") or {}
      # el = self.event_handlers or {}
      # for ekey in self.event_handlers.keys():
      #   if topic.startswith(ekey):
      #     for action_item in el.get(ekey) or []:
      #       action = action_item.get("action")
      #       if hasattr(self, action):
      #         method = getattr(self, action)
      #         if method:
      #           method(epack)


    def on_data(self, data):
      # print("ON DATA", data)
      # print(f"onData self = {self.identity}", flush=True)
      # print(f"DATA Handles: {self.data_handlers}", flush=True)
      for d in self.data_handlers:
        data = d.handle(data)

      self.zmq_pub.send_multipart(data)
        
    
    def handle_route(self, replyto, seq, request):
      action = request["action"]
      if hasattr(self, action):
        method = getattr(self, action)
        if method:
            # out = call_maybe_yield(route.call, *[request], **args)

          res = method(request["body"])
        else:
          newres = b'{"error": "No Method"}'
          self.zmq_router.send_multipart([replyto, seq, newres])
          return

      # res = self._handle(environ)
      
      # print(typing.co, flush=True)
      # if isinstance(res, CoroutineType):
      if yields(res):
        future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
        print("FUTURE = ", future)
        zmqrouter = self.zmq_router
        def onfinish(fut):
          newres = fut.result(1)
          status = b'success'
          if "error" in newres:
            status = b'error'
          zmqrouter.send_multipart([replyto, seq, json.dumps(newres).encode('ascii')])

        future.add_done_callback(onfinish)

      else:
        print(f"THE RESP here = {res}", flush=True)
        if not res:
          res = {"success": "ok"}

        self.zmq_router.send_multipart([replyto, seq, json.dumps(res).encode('ascii')])


    def router_message_sent(self, msg, status):
      print(f"INSIDE ROUTE SEND {msg}", flush=True)

    def router_message(self, msg):
      print("INSIDE ROUTE message", flush=True)
      print(f"Router Msg = {msg}", flush=True)
      
      replyto, seq_s, brequest, *args = msg
      # seq = struct.unpack('!q',seq_s)[0]
      # action = action.decode('utf-8')
      request = brequest.decode('utf-8')
      try:
        req = json.loads(request)
        self.handle_route(replyto, seq_s, req)
      except Exception as e:
        print(f'PROCESS EXCEPTION {str(e)}')

      # if action == "connect":
      #   self.connect(0)
      #   self.zmq_router.send_multipart([replyto, b'connect', b'tada'])
      # elif action == "video_processor":
      #    = self.get_or_create_video_processor()
      #   self.zmq_router.send_multipart([replyto, b'video_processor', b'tada'])
      # el = self.event_handlers or {}
      # for ekey in self.event_handlers.keys():
      #   if action.startswith(ekey):
      #     for action_item in el.get(ekey) or []:
      #       action = action_item.get("action")
        # if hasattr(self, action):
        #   method = getattr(self, action)
        #   if method:
        #     method(epack)

      # params = {}
      # if len(args):
      #   try:
      #     params = json.loads(args.pop().decode('utf-8'))
      #   except Exception as e:
      #     print(f"Could not load params: {str(e)}", flush=True)
      
      # environ = {"REQUEST_METHOD": method.upper(), "PATH": path, "params": params}
      # res = self._handle(environ)
      # # print(typing.co, flush=True)
      # # if isinstance(res, CoroutineType):
      # if yields(res):
      #   future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
      #   print("FUTURE = ", future)
      #   zmqrouter = self.zmq_router
      #   def onfinish(fut):
      #     newres = fut.result(1)
      #     status = b'success'
      #     if "error" in newres:
      #       status = b'error'
      #     zmqrouter.send_multipart([replyto, status, json.dumps(newres).encode('ascii')])

      #   future.add_done_callback(onfinish)

      # else:
      #   print(f"THE RESP here = {res}", flush=True)
      #   status = b'success'
      #   if "error" in res:
      #     status = b'error'
      #   self.zmq_router.send_multipart([replyto, status, json.dumps(res).encode('ascii')])
      # # node_identity, request_id, device_identity, action, *msgparts = msg
      # return "Routed"

    def fire_event(self, evtname, payload):
      # print(f"fire event {evtname}", flush=True)
      if isinstance(evtname, Event):
        evtname = evtname.value()
      evtname = evtname.encode('ascii')
      # payload["device"] = self.name
      pstring = json.dumps(payload, cls=ServiceJsonEncoder)
      print(f"JSON DUMP = {pstring}", flush=True)
      pstring = pstring.encode('ascii')
      self.zmq_pub.send_multipart([b'events.'+ evtname, self.identity, pstring])

    async def _process_tasks(self):
      # print("About to get queue", flush=True)
      async for dtask in self.task_queue:
        # print('consuming {}...'.format(item))
        self.current_task[dtask.name] = dtask
        res = await dtask.run(self)
        rj = json.dumps(res, cls=ServiceJsonEncoder).encode('ascii')
        self.zmq_pub.send_multipart([self.identity+b'.task', b'finished', rj])

        # self.pusher.publish()
        del self.current_task[dtask.name]
        print(f"PROCESS TASK = {res}", flush=True)


    def connect(self, data):
      endpoint = data.get("endpoint")
      print(f"Camera Connect {os.getpid()}", flush=True)
      self.connector = CameraConnector(self.ctx, self.identity, endpoint)
      self.connector.open()
      
      self.connector.run()
      # self.state.connected = True
      print(f"Cam {os.getpid()} and {CameraRecording._meta.database.__dict__}")
      # tcr = CameraRecording(task_name="bob", settings={}, status="pending")
      # tcr.save()

      self.fire_event(CameraEvent.connection.opened, {"status": "success"})
      return {"status": "connected"}

    def stop(self, *args):
      print("Camera Stop", flush=True)
      if self.connector:
        self.connector.close()
      self.connector = None
      # self.state.connected = False
      self.fire_event(CameraEvent.connection.closed, {"status": "success"})

    def get_or_create_video_processor(self, *args):
      # if not self.state.connected:
      #   raise AncillaError(400, {"error": "Camera Not Connected"})
      
      if self.video_processor:
          for k, v in self.current_task.items():
            if isinstance(v, CameraProcessVideoTask):    
              return {"stream": v.processed_stream}
              # return v

      
      
      # print(f'tc = {tcr}', flush=True)
      payload = {"settings": {}}
      self.video_processor = CameraProcessVideoTask("process_video", self, payload)
      self.task_queue.put(self.video_processor)
      loop = IOLoop().current()
      loop.add_callback(partial(self._process_tasks))
      return {"stream": self.video_processor.processed_stream}


    def get_recording_task(self, data):
      try:

        task_name = data.get("task_name")
        cr = None
        if data.get("recording_id"):
          cr = CameraRecording.get_by_id(data.get("recording_id"))
          task_name = cr.task_name

        printmodel = data.get("model")
      
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

      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    def stop_recording(self, msg):
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.cancel()
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

    def start_recording(self, msg):
      # print(f"START RECORDING {msg}", flush=True)
      # print(f"RECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      # return {"started": True}
      try:
        
        
        payload = msg.get('data')
        name = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))

        
        pt = CameraRecordTask(name, self, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(partial(self._process_tasks))
        return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not record {str(e)}"}




