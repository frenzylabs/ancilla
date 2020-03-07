'''
 http_server.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import os
import tornado
from tornado import gen
from tornado.ioloop import IOLoop
from tornado.web    import Application, RequestHandler, StaticFileHandler

import socket

import asyncio
import atexit

# Local imports
from ..env import Env

# Resources
from .resources import (
  FileResource,
  PortsResource,
  DocumentResource,
  WebcamHandler,
  LayerkeepResource,
  WifiResource,
  SystemResource,
  StaticResource
)

from .resources.node_api import NodeApiHandler

from ..data.models import Service

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui/dist')


import zmq
from zmq.eventloop.zmqstream import ZMQStream


from tornado.websocket import WebSocketHandler
import json
import time

from datetime import datetime



class ZMQNodePubSub(object):

    def __init__(self, node, request_callback, subscribe_callback):

        self.callback = request_callback
        self.subscribe_callback = subscribe_callback
        self.node = node

    def connect(self):
        # print("Node PUbsub connect", flush=True)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        # self.socket.identity = b'tada123'
        # print(f'ConnecT to Router {self.node.router_address}')
        self.socket.connect(self.node.router_address)

        self.stream = ZMQStream(self.socket)
        self.stream.setsockopt( zmq.LINGER, 0 )
        self.stream.on_recv(self.callback)

        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(self.node.publisher_address)

        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.setsockopt( zmq.LINGER, 0 )
        # self.subscriber.setsockopt( ZMQ:IMMEDIATE)
        self.subscriber.on_recv(self.subscribe_callback)
        


    def subscribe(self, to, topic=''):
      subscribeto = to
      if len(topic) > 0:
        subscribeto = f"{subscribeto}.{topic}"
      subscribeto = self.node.identity + b'.' + subscribeto.encode('ascii')

      self.subscriber.setsockopt(zmq.SUBSCRIBE, subscribeto)
    
    def unsubscribe(self, to, topic=''):
      subscribetopic = to
      if len(topic) > 0:
        subscribetopic = f"{subscribetopic}.{topic}"
      subscribetopic = subscribetopic.encode('ascii')


      self.subscriber.setsockopt(zmq.UNSUBSCRIBE, subscribetopic)

    def close(self):
      if self.subscriber:
        self.subscriber.stop_on_recv()
        self.subscriber.close()
        self.subscriber = None
      if self.stream:
        self.stream.stop_on_recv()
        self.stream.close()
        self.stream = None
      

    def make_request(self, target, action, msg = None):
      kind, *cmds = action.split(".")
      method = action
      if len(cmds) > 0:
        method = cmds[0]

      wrapped = {"data": msg}
      # send_to_socket = [self.node.identity, method.encode('ascii'), json.dumps(wrapped).encode('ascii')]
      # print(f'Sending {send_to_socket}')
      # self.stream.send_multipart(send_to_socket)
      # self.socket.send_multipart([method.encode('ascii'), json.dumps(wrapped).encode('ascii'), target.encode('ascii')])
      
      return self.node.run_action(method, wrapped, target) 


class NodeSocket(WebSocketHandler):
    def __init__(self, application, request, **kwargs) -> None:
        self.node = kwargs.pop('node', None)
        self.timer = time.time()
        self.node_connector = ZMQNodePubSub(self.node, self.on_data, self.subscribe_callback)
        self.node_connector.connect()
        self.node_connector.subscribe("notifications")
        self.last_printer_command = ""
        super().__init__(application, request, **kwargs)


    def check_origin(self, origin):
      return True

    def open(self, *args, **kwargs):
        subscription = ""
        if (len(args) > 0):
          subscription = args[0]

        self.subscription = subscription
    
    def subscribe_callback(self, data):
      # print("SUBSCRIBE CB", flush=True)
      if data and len(data) > 2:
        topic, status, msg, *other = data

        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        senddata = True
        try:
          msg = json.loads(msg)
          if (topic.endswith('printer.data_received')):
            if msg.get("command") and msg.get("req_id") != 0:              
              if (time.time() - self.timer) > 2:
                self.timer = time.time()
              else:
                senddata = False
          
          
        except Exception as e:
          print(f"SubscribeEXCE = {str(e)}")
          senddata = False
          pass

        if senddata:
          self.write_message(json.dumps([topic, msg]))


    def on_message(self, message):
        # print(f'MSG: {message}', flush=True)

        to = ""
        try:
          msg     = json.loads(message)
          target = msg.pop(0)
          action = None
          
          action = msg.pop(0)
          content = None
          if (len(msg) > 0):
            content = msg.pop(0)

          if action == 'SUB':
            self.node_connector.subscribe(target, content)
          elif action == 'UNSUB':
            self.node_connector.unsubscribe(target, content)
          else:

            res = self.node_connector.make_request(target, action, content)
            if res:
              self.write_message(json.dumps(res))
        except Exception as err:
          print("Server API EXCEPTION", flush=True)
          print(str(err), flush=True)
          self.write_message(json.dumps([to+".request", {"error": str(err)}]))

        
    
    def on_close(self):
      self.node_connector.close()

    def on_data(self, data):
      # print(f"WS ON DATA {data}", flush=True)
      node_identifier, to, msg = data
      msg = msg.decode('utf-8')
      try:
        msg = json.loads(msg)
      except:
        pass
      to = to.decode('utf-8')
      self.write_message(json.dumps([to, msg]))


class APIServer(object):
  def __init__(self, document_store, node_server):
    self.document_store = document_store
    self.node_server = node_server
    # self.discovery = discovery
    # atexit.register(self.cleanup)

  def cleanup(self):
    print(f"cleanup api server")
    self.stop()

  @property
  def app(self):
    settings = {
      'debug' : Env.get('RUN_ENV') == 'DEV',
      'static_path' : STATIC_FOLDER      
    }

    _app = Application([      
      (r"/api/system(.*)",  SystemResource, dict(node=self.node_server)),
      (r"/api/document",  DocumentResource, dict(document=self.document_store)),
      (r"/api/wifi(.*)",  WifiResource, dict(node=self.node_server)),
      (r"/api/files",     FileResource, dict(node=self.node_server)),
      (r"/api/files(.*)",     FileResource, dict(node=self.node_server)),
      (r"/api/layerkeep(.*)",     LayerkeepResource, dict(node=self.node_server)),
      (r"/api/ports",     PortsResource),
      (r"/api/webcam/(.*)",   WebcamHandler, dict(node=self.node_server)),
      (r"/api/services/(.*)",   NodeApiHandler, dict(node=self.node_server)),
      (r"/api/services",   NodeApiHandler, dict(node=self.node_server)),
      (r"/api/(.*)",   NodeApiHandler, dict(node=self.node_server)),
      (r"/node/(.*)",   NodeApiHandler, dict(node=self.node_server)),
      (r"/node",   NodeApiHandler, dict(node=self.node_server)),
      (r"/ws",   NodeSocket, dict(node=self.node_server)),
      
      (r"/app/(.*)",  StaticFileHandler, dict(path = STATIC_FOLDER)),
      
      (r"/static/(.*)",  StaticFileHandler, dict(path = STATIC_FOLDER)),
      (r"/(.*)",  StaticResource, dict(path = STATIC_FOLDER, default_filename = "index.html")),
      
    ], **settings)

    return _app



  def start(self):
    print("Starting api server...", flush=True)
    if not IOLoop.current(instance=False):
      loop = IOLoop().initialize(make_current=True)  

    trybind = 30
    bound = False
    while not bound and trybind > 0:
      try:
        print(f'Node Service api port = {self.node_server.api_port}')
        self.app.listen(self.node_server.api_port, **{'max_buffer_size': 10485760000})

        print(f"Bound to {self.node_server.api_port}")
        bound = True
      except OSError as e:
        trybind -= 1
        self.node_server.api_port += 1

      except Exception as e:
        print(f'Start Exception = {str(e)}')
        trybind -= 1
        self.node_server.api_port += 1

    # self.app.listen(self.node_server.api_port, **{'max_buffer_size': 10485760000})
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()
