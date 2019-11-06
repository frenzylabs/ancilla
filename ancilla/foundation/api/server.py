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


import threading

import asyncio

# Local imports
from ..env import Env

# Resources
from .resources import (
  FileResource,
  PrinterResource,
  PortsResource,
  DocumentResource
)

# Sockets
from ..socket import (
  SerialResource
)

from ..data.models import Device, DeviceRequest

STATIC_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ui/dist')


import zmq
from zmq.eventloop.zmqstream import ZMQStream


from tornado.websocket import WebSocketHandler
import json
import time

import cv2
import h5py
from datetime import datetime




class ZMQNodePubSub(object):

    def __init__(self, node, request_callback, subscribe_callback):
        self.callback = request_callback
        self.subscribe_callback = subscribe_callback
        self.node = node

    def connect(self):
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        # url_worker = "ipc://backend.ipc"
        # url_client = "inproc://frontend"
        # self.socket.connect('tcp://127.0.0.1:5560')
        self.socket.connect('tcp://127.0.0.1:5556')
        # self.socket.connect(url_client)
        self.stream = ZMQStream(self.socket)
        self.stream.on_recv(self.callback)

        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect('ipc://publisher')
        # self.request.connect('tcp://127.0.0.1:5557')
        # self.request.connect('ipc://devicepublisher')
        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.on_recv(self.subscribe_callback)
        

        # self.request.linger = 0
        # self.request.setsockopt(zmq.SUBSCRIBE, b"")

    def subscribe(self, to, topic=''):
      subscribeto = to
      if len(topic) > 0:
        subscribeto = f"{subscribeto}.{topic}"
      subscribeto = subscribeto.encode('ascii')
      print("topic = ", subscribeto)
      # if callback:
      #   self.subscriber.on_recv(callback)
      self.subscriber.setsockopt(zmq.SUBSCRIBE, subscribeto)
    
    def unsubscribe(self, to, topic=''):
      subscribetopic = to
      if len(topic) > 0:
        subscribetopic = f"{subscribetopic}.{topic}"
      subscribetopic = subscribetopic.encode('ascii')

        # if type(topic) != bytes:
        #   topic = topic.encode('ascii')
      print("subtopic= ", subscribetopic)
        # self.request.on_recv(callback)
      self.subscriber.setsockopt(zmq.UNSUBSCRIBE, subscribetopic)


    def make_request(self, to, action, msg = None):
      device = Device.select().where(Device.name == to)
      if len(device) > 0:
        device = device.get()
      else:
        raise Exception(f"No Device With Name {to}")
    
      if msg and type(msg) == dict:
        msg = json.dumps(msg)

      print("device = ", device)
      dr = DeviceRequest(device_id=device.id, status="pending", action=action, payload=msg)
      dr.save()
      print(dr, flush=True)
      payload = [self.node.identity, f'{dr.id}'.encode('ascii'), to.encode('ascii'), action.encode('ascii')]
      if msg:
        payload.append(msg.encode('ascii'))

      self.socket.send_multipart(payload)


class NodeSocket(WebSocketHandler):
    def __init__(self, application, request, **kwargs) -> None:
        print(kwargs, flush=True)
        # node = kwargs.get("node")
        self.node = kwargs.pop('node', None)
        super().__init__(application, request, **kwargs)


    def open(self, *args, **kwargs):
        subscription = ""
        if (len(args) > 0):
          subscription = args[0]
        
        print("OPEN NODE SOCKET", flush=True)
        self.subscription = subscription
        self.pubsub = ZMQNodePubSub(self.node, self.on_data, self.subscribe_callback)
        self.pubsub.connect()
        self.pubsub.subscribe(self.node.identity.decode('utf-8'))
        # self.node.connect("tcp://localhost:5556", "localhost")
        # self.node.add_device("Printer", "/dev/cu.usbserial-14140", subscription)
        # self.node.add_device('camera', '0', subscription)
        
        # self.pubsub.subscribe("")
        print('ws node opened')
    
    def subscribe_callback(self, data):
      print("SUBSCRIBE CB", flush=True)
      print(data, flush=True)
      if data and len(data) > 2:
        topic, status, msg, *other = data
        # print(topic, flush=True)
        self.write_message(msg, binary=True)
      # self.write_message("HI")

    def on_message(self, message):
        print(f'MSG: {message}', flush=True)
        
        # self.pubsub.stream.send([b'', '', message.encode("ascii")])
        # self.pubsub.stream.send(message.encode("ascii"))
        # self.pubsub.socket.send_multipart([b'', b'', message.encode("ascii")])
        # self.write_message(message, binary=True)

        try:
          msg     = json.loads(message)
          # print(msg, flush=True)
          to = msg.pop(0)
          action = None
          data = []
          
          action = msg.pop(0)
          content = None
          if (len(msg) > 0):
            content = msg.pop(0)

          # ['CONTROL', 'ADD|REMOVE' ]
          # ['to', 'SUBSCRIBE', '']
          if to == "CMD":
            if action == "ADD":
              kind = content.get("kind")
              name = content.get("name")
              res = self.node.add_device(kind, name)
              print(res, flush=True)
              self.write_message(res, binary=True)
          elif action == 'SUB':
            self.pubsub.subscribe(to, content)
          elif action == 'UNSUB':
            self.pubsub.unsubscribe(to, content)
          else:

            res = self.pubsub.make_request(to, action, content)
        except Exception as err:
          print("EXCEPTION", flush=True)
          print(str(err), flush=True)
          self.write_message({"error": str(err)})

        
    
    def on_close(self):
        print('ws closed')

    def on_data(self, data):
        # print(f"WS ON DATA {data}", flush=True)
        # print(data, flush=True)
        node_identifier, request_id, msg = data
        # print(node_identifier, flush=True)
        self.write_message(msg, binary=True)
        # if sub == self.subscription:
        #   data = self.pubsub.request.recv_pyobj()
        #   print(data)
        
        # image = cv2.cvtColor(msg, cv2.COLOR_BGR2RGB)
        # cv2.imshow('image',image)
        # cv2.waitKey(0)

        # print(msg, flush=True)
        # if sub == 'camera'
        # frame = pickle.loads(msg)

        # with h5py.File('camera_data.hdf5', 'a') as file:
        #   now = str(datetime.now())
        #   g = file.create_group(now)

        #   # topic = socket.recv_string()
        #   # frame = socket.recv_pyobj()

        #   x = frame.shape[0]
        #   y = frame.shape[1]
        #   z = frame.shape[2]

        #   dset = g.create_dataset('images', (x, y, z, 1), maxshape=(x, y, z, None))
        #   dset[:, :, :, 0] = frame
        #   i=0
        #   # while True:
        #   #     i += 1
        #   #     topic = socket.recv_string()
        #   #     frame = socket.recv_pyobj()
        #   #     dset.resize((x, y, z, i+1))
        #   #     dset[:, :, :, i] = frame
        #   #     file.flush()
        #   #     print('Received frame number {}'.format(i))
        #   #     if i == 20:
        #   #         break

        
        # self.write_message({"message": data[0].decode("utf-8")})


class APIServer(object):
  def __init__(self, document_store, node_server):
    print("INIT")
    self.document_store = document_store
    self.node_server = node_server


  @property
  def app(self):
    settings = {
      'debug' : Env.get('RUN_ENV') == 'DEV',
      'static_path' : STATIC_FOLDER
    }

    _app = Application([
      (r"/document",  DocumentResource, dict(document=self.document_store)),
      (r"/files",     FileResource, dict(node=self.node_server)),
      (r"/printers",  PrinterResource),
      (r"/ports",     PortsResource),
      (r"/serial",    SerialResource),
      (r"/node/(.*)",   NodeSocket, dict(node=self.node_server)),
      # (r"/webcam/(.*)",   StreamHandler),
      (r"/app/(.*)",  StaticFileHandler, dict(path = STATIC_FOLDER)),
    ], **settings)

    return _app

  def start(self):
    print("Starting api server...", flush=True)

    # server = tornado.httpserver.HTTPServer(self.app)
    # server.bind(5000)
    # server.start(0)
    self.app.listen(5000)
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()
