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
from ...request import Request
from ...app import App, ConfigDict

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


class CameraProcess():
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

    def __init__(self, identity, **kwargs): 
        # ctx = mp.get_context('spawn')
        # ctx.set_start_method('spawn')
        # ctx.Process.__init__(self)
        # super().__init__(**kwargs)
        # self.service = service
        self.identity = identity
        
        self.loop = None
        print(f"PROCESS ID + {os.getpid()}", flush=True)
        # self.rpc, self.child_conn = Pipe()
        self.router_address = None



        # self.parent_conn, child_conn = ctx.Pipe()
        # self.p = ctx.Process(target=self.run, args=(self.child_conn,))
        # self.p.daemon = True
        
        
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

    
    @classmethod
    def start_process(cls, identity, child_conn):
      inst = cls(identity)
      inst.run(child_conn)

    def stop_process(self):
      print(f'INSIDE PROCESS stop_process here', flush=True)
      
      if self.connector:
        self.connector.close()
      if self.video_processor:
        print(f"Close video processor")
        self.video_processor.close()
      for k, v in self.current_task.items():
        if hasattr(v, "stop"):
            v.stop()
      self.fire_event(CameraEvent.connection.closed, {"status": "success"})
      self.data_stream.close()
      self.zrouter.close()
      # self.zpub.close()
      

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

    def state_changed(self, event, oldval, key, newval):
      print("state changed")

      
    def setup(self):
      print(f'SETUP PROCESS')
      from ....env import Env
      from ....data.db import Database
      from playhouse.sqlite_ext import SqliteExtDatabase
      import zmq
      import cv2
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
      
      # PrinterCommand._meta.database = conn

      self.state = ConfigDict()._make_overlay()
      self.state._add_change_listener(partial(self.state_changed, 'state'))
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

      # self.heartbeat = PeriodicCallback(self.send_state, 6000)        
      # self.heartbeat.start()
      
      print(f"INSIDE run loop {self.loop}")
      # self.loop.start()
      # self.loop.run_forever()
      # print("AFTER LOOP")
      # child_conn = self.child_conn
      self.child_conn = child_conn
      while self.running:
        res = child_conn.poll(0.01)
        if res:
          try:
            payload = child_conn.recv()
          except:
            break
          if payload:
            (key, args) = payload
            if key == "router_address":
              child_conn.send((key, self.router_address))
            elif key == "pubsub_address":
              child_conn.send((key, self.pubsub_address))
            elif key == "stop":
              print(f'INSIDE Self.running key=stop', flush=True)
              self.stop_process()              
              child_conn.send((key, "success"))
              time.sleep(2)
              self.running = False              
              break
        await asyncio.sleep(1)


    def run(self, child_conn):
      # asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
      self.running = True
      try:
          # loop = ZMQEventLoop()
        print("RUN CAM PROCESS")
        evtloop = asyncio.new_event_loop()
        asyncio.set_event_loop(evtloop)
        # self.run_loop(evtloop)
        evtloop.run_until_complete(self.run_loop(evtloop, child_conn))
        print("RUN CAM PROCESS COMPLETE")
      except KeyboardInterrupt:
        self.stop_process()              
        child_conn.send(("stop", "success"))
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

      if hasattr(self, "zmq_pub"):
        self.zmq_pub.send_multipart(data)
        
    
    def handle_route(self, replyto, seq, request):
      action = request["action"]
      if hasattr(self, action):
        method = getattr(self, action)
        if method:
            # out = call_maybe_yield(route.call, *[request], **args)
          res = b''
          try:
            res = method(request["body"])
          except AncillaResponse as ar:
            res = ar
          except Exception as e:
            res = AncillaError(404, {"error": str(e)})
        else:
          # newres = b'{"error": "No Method"}'
          res = AncillaError(404, {"error": "No Method"})
          # self.zmq_router.send_multipart([replyto, seq, err.encode()])
          # return

      if yields(res):
        future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
        print("FUTURE = ", future)
        zmqrouter = self.zmq_router
        def onfinish(fut):
          res = b''
          try:
            newres = fut.result(1)
            if isinstance(newres, AncillaResponse):
              res = newres.encode()
            else:
              res = AncillaResponse(newres).encode()          
          except AncillaResponse as ar:
            res = ar.encode()

          zmqrouter.send_multipart([replyto, seq, res])

        future.add_done_callback(onfinish)

      else:
        print(f"THE RESP here = {res}", flush=True)
        if not res:
          res = {"success": "ok"}
        if isinstance(res, AncillaResponse):
          res = res.encode()
        else:
          res = AncillaResponse(res).encode()

        self.zmq_router.send_multipart([replyto, seq, res])


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
        classname = req.get('__class__')
        print(f'classname = {classname}')
        # module = __import__(module_name)
        
        module_name, class_name = classname.rsplit(".", 1)
        MyClass = getattr(importlib.import_module(module_name), class_name)
        # cvmodule = sys.modules.get(classname)
        print(f'Process cmod = {MyClass}')
        instance = MyClass(**req.get('data', {}))
        print(f'Instance = {instance}')
        self.handle_route(replyto, seq_s, instance)
      except Exception as e:
        print(f'PROCESS EXCEPTION {str(e)}')


    def fire_event(self, evtname, payload):
      # print(f"fire event {evtname}", flush=True)
      if not hasattr(self, "zmq_pub"):
        return

      if isinstance(evtname, Event):
        evtname = evtname.value()
      evtname = evtname.encode('ascii')
      # payload["device"] = self.name
      pstring = json.dumps(payload, cls=ServiceJsonEncoder)
      print(f"FireEvt: {evtname} JSON DUMP = {pstring}", flush=True)
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
      self.state.connected = True
      print(f"Cam {os.getpid()} and {CameraRecording._meta.database.__dict__}")
      # tcr = CameraRecording(task_name="bob", settings={}, status="pending")
      # tcr.save()

      self.fire_event(CameraEvent.connection.opened, {"status": "success"})
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

    def pause_recording(self, msg):
        payload = msg.get('data')
        task = self.get_recording_task(payload)
        if task:
          task.pause()
          return {"status": "success"}
        else:
          return {"status": "error", "error": "Task Not Found"}

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

    def start_recording(self, msg):
      print(f"START RECORDING {msg}", flush=True)
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
        raise AncillaError(400, {"status": "error", "error": f"Could not record {str(e)}"}, exception=e)
        # return {"status": "error", "error": f"Could not record {str(e)}"}




