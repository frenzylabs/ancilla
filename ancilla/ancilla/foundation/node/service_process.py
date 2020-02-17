'''
 service_process.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/29/20
 Copyright 2019 FrenzyLabs, LLC.
'''



import logging
import sys
import time
import zmq
import importlib

import os

import json
from playhouse.signals import Signal, post_save, post_delete

from ..data.models import Service
from ..utils.service_json_encoder import ServiceJsonEncoder

from functools import partial
from tornado.queues     import Queue

import struct # for packing integers


from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop

import inspect
import asyncio

from .events import Event, EventPack, State as StateEvent

from .response import AncillaResponse, AncillaError
from .request import Request
from ..utils import yields
from ..utils.dict import ConfigDict

import resource, gc, signal
import psutil


class ServiceProcess():


    def __init__(self, identity, service_id, child_conn, handler, **kwargs): 

        self.identity = identity
        self.model = Service.get(Service.id == service_id)
        self.child_conn = child_conn
        self.data_handlers = []      
        self.handler = handler(self)
        
        self.loop = None

        self.router_address = None

        self.setup_event_loop()
        self.setup()

        self.ctx = zmq.Context.instance()
        self.port = 5557
        self.pub_port = 5558

        self.setup_router()
        self.zmq_router = ZMQStream(self.zrouter, self.loop)
        self.zmq_router.on_recv(self.router_message)

        self.setup_publiser()
        self.zmq_pub = ZMQStream(self.zpub, self.loop)

        self.setup_data()

        
        # self.limit_memory()
        # soft, hard = resource.getrlimit(resource.RLIMIT_AS) 
        # print(f'MEM limit NOW = {soft}, {hard}')


    
    @classmethod
    def start_process(cls, identity, service_id, child_conn, handler):      
      inst = cls(identity, service_id, child_conn, handler)
      inst.run()

  
    def _hangle_sig_memory(self, signum, stack):
      print("handle memory sig")
      gc.collect()

    def limit_memory(self): 
      maxhard = psutil.virtual_memory().available
      maxsoft = maxhard / 2
      p = psutil.Process(pid=os.getpid())
      soft, hard = resource.getrlimit(resource.RLIMIT_AS) 
      h = min([maxhard, hard])
      if hasattr(p, 'rlimit'):
        # soft, hard = p.rlimit(resource.RLIMIT_AS) 
        print(f'Service MEM limit = {soft}, {hard}: {h}')
        
        p.rlimit(resource.RLIMIT_AS, (maxsoft, h))
      else:
        
        print(f'Service MEM limit = {soft}, {hard}:  {h}')
        resource.setrlimit(resource.RLIMIT_AS, (maxsoft, h))
      self._old_usr1_hdlr = signal.signal(signal.SIGUSR1, self._hangle_sig_memory)

    def setup(self):
      from ..env import Env
      from ..data.db import Database
      from playhouse.sqlite_ext import SqliteExtDatabase
      import zmq
      Env.setup()
      
      conn = SqliteExtDatabase(Database.path, pragmas=(
        ('cache_size', -1024 * 64),  # 64MB page-cache.
        ('journal_mode', 'wal'),  # Use WAL-mode (you should always use this!).
        ('foreign_keys', 1),
        ('threadlocals', True)))
      Database.conn.close()
      Database.conn = conn
      Database.connect()

      self.state = ConfigDict()._make_overlay()
      self.state._add_change_listener(partial(self.state_changed, 'state'))
      self.task_queue = Queue()
      self.current_tasks = {}
      self.video_processor = None

    def model_updated(self):
      print(f"ServiceProcess POST SAVE HANDLER")
      # if self.model.id != instance.id:
      #   return
      
      self.model = Service.get_by_id(self.model.id)
      if hasattr(self.handler, "model_updated"):
        self.handler.model_updated()

    def setup_event_loop(self):
      self.evtloop = asyncio.new_event_loop()
      asyncio.set_event_loop(self.evtloop)

      IOLoop.clear_current()
      if hasattr(IOLoop, '_current'):
        del IOLoop._current

      if self.loop is None:
          if not IOLoop.current(instance=False):
              self.loop = IOLoop.current() #IOLoop()
          else:
              self.loop = IOLoop.current()

      
    def stop_process(self):
      if self.handler:
        self.handler.close()

      for k, v in self.current_tasks.items():
        if hasattr(v, "stop"):
            v.stop()

      self.data_stream.close()
      self.zrouter.close()
      # if we close zpub here we wont get the last messages
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
        deid = f"inproc://{self.identity}_collector"
        self.data_stream = self.ctx.socket(zmq.PULL)
        self.data_stream.bind(deid)

        self.data_stream = ZMQStream(self.data_stream)
        self.data_stream.linger = 0
        self.data_stream.on_recv(self.on_data)

    def state_changed(self, event, oldval, key, newval):
      # print(f"state changed {self.state}, key={key} OLDVAL: {oldval}, {newval}", flush=True)
      dict.__setitem__(oldval, key, newval)
      self.fire_event(StateEvent.changed, oldval)

    async def run_loop(self):

      child_conn = self.child_conn
      while self.running:
        res = child_conn.poll(0)
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
            elif key == "model_updated":
              self.model_updated()
            elif key == "stop":
              self.stop_process()              
              child_conn.send((key, "success"))
              time.sleep(2)
              self.running = False              
              break
        await asyncio.sleep(2)


    def run(self):
      self.running = True
      try:
        self.evtloop.run_until_complete(self.run_loop())
      except KeyboardInterrupt:
        self.stop_process()              
        self.child_conn.send(("stop", "success"))
        self.running = False
        print('\nProcessFinished (interrupted)')
    

    def on_data(self, data):
      for d in self.data_handlers:
        data = d.handle(data)

      if hasattr(self, "zmq_pub"):
        self.zmq_pub.send_multipart(data)
        
    
    def handle_route(self, replyto, seq, request):
      action = request["action"]
      if hasattr(self.handler, action):
        method = getattr(self.handler, action)
        if method:
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

      if yields(res):
        future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
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
        if not res:
          res = {"success": "ok"}
        if isinstance(res, AncillaResponse):
          res = res.encode()
        else:
          res = AncillaResponse(res).encode()

        self.zmq_router.send_multipart([replyto, seq, res])


    def router_message(self, msg):
      # print(f"Router Msg = {msg}", flush=True)
      
      replyto, seq_s, brequest, *args = msg
      # seq = struct.unpack('!q',seq_s)[0]
      # action = action.decode('utf-8')
      request = brequest.decode('utf-8')
      try:
        req = json.loads(request)
        classname = req.get('__class__')

        module_name, class_name = classname.rsplit(".", 1)
        MyClass = getattr(importlib.import_module(module_name), class_name)

        instance = MyClass(**req.get('data', {}))
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
      pstring = pstring.encode('ascii')
      self.zmq_pub.send_multipart([b'events.'+ evtname, self.identity, pstring])

    def add_task(self, task):
      self.task_queue.put(task)
      loop = IOLoop().current()
      loop.add_callback(partial(self._process_tasks))

    async def _process_tasks(self):
      async for dtask in self.task_queue:
        # print('process task {}...'.format(dtask))
        self.current_tasks[dtask.name] = dtask
        res = await dtask.run(self)
        rj = json.dumps(res, cls=ServiceJsonEncoder).encode('ascii')
        self.zmq_pub.send_multipart([self.identity+b'.task', b'finished', rj])

        del self.current_tasks[dtask.name]
        print(f"PROCESS TASK {self.identity} DONE= {res}", flush=True)

