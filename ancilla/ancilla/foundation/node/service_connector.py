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

import struct # for packing integers

from zmq.eventloop.zmqstream import ZMQStream

import asyncio


# from multiprocessing import Process, Pipe
import multiprocessing as mp


from .response import AncillaResponse, AncillaError
from .request import Request

from .base_service import BaseService
from ..utils.service_json_encoder import ServiceJsonEncoder


from .service_process import ServiceProcess



global SEQ_ID
SEQ_ID = 0


class ServiceConnector():

    def __init__(self, service, handler, **kwargs): 
        processCtx = mp.get_context('spawn')

        self.service = service
        self.name_identity = service.encoded_name
        self.identity = service.identity #f"service{self.service.model.id}".encode('ascii')
        
        self.loop = None
        
        self.router_address = None
        self.rpc_router = None
        self.process_event_stream = None
        self.requests = {}
        self.ctx = zmq.Context()
        
        self.rpc, self.child_conn = mp.Pipe()
        self.p = processCtx.Process(target=ServiceProcess.start_process, args=(self.identity, self.child_conn, handler))
        
        
    def start(self, *args):
      print(f'Start Process {self.p}')
      self.p.start()
      self.setup_queue()

    def stop(self, *args):
      print(f'Stop Process 1')
      self.rpc.send(("stop", ""))
      cnt = 10
      while cnt > 0:
        res = self.rpc.poll(1)
        if res:
          tada = self.rpc.recv()
          break 

        cnt -= 1

      self.p.join(2)
      # self.p.terminate()
      self.p = None
      print(f'Stopped Process')
      if self.rpc_router:
        self.rpc_router.close()
        
      if self.process_event_stream:
        self.process_event_stream.flush()
        self.process_event_stream.close()

      
    def setup_queue(self):
      rpc_router = self.ctx.socket(zmq.ROUTER)

      waitcnt = 100
      while waitcnt > 0 and not self.is_alive():
        time.sleep(0.1)
        waitcnt -= 1
      time.sleep(0.5)
      router_address = self.get_router_address()
      rpc_router.connect(router_address)

      self.rpc_router = ZMQStream(rpc_router)
      self.rpc_router.on_recv(self.router_message)

      self.pubsub_address = self.get_pubsub_address()
      process_event_stream = self.ctx.socket(zmq.SUB)
      process_event_stream.connect(self.pubsub_address)
      self.process_event_stream = ZMQStream(process_event_stream)
      self.process_event_stream.linger = 0
      self.process_event_stream.on_recv(self.on_process_event)

      self.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'events')


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
      
    def on_process_event(self, msg):
      # print(f"CAM PUBSUB Msg = {msg}", flush=True)
      topic, identity, *res = msg
      if topic.startswith(b'data'):
        topic = self.service.encoded_name + b'.' + topic
      
      if topic.startswith(b'events.state'):
        try:
          newstate = json.loads(res[0].decode('utf-8'))
          self.service.state.update(newstate)
        except:
          pass
        

      nmsg = [topic, self.service.encoded_name] + res
      # print(f"Process evt: {nmsg}")
      self.service.pusher.send_multipart(nmsg)

    def router_message(self, msg):
      # print(f"Router Result = {msg}", flush=True)
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

      self.rpc_router.send_multipart([self.identity, seq_s, renc])

      res = await fut
      try:
        del self.requests[seq_s]
        res = json.loads(res.decode('utf-8'))
        classname = res.get('__class__')

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

