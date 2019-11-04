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

    def __init__(self, node, callback):
        self.callback = callback
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

        self.request = self.context.socket(zmq.SUB)
        self.request.connect('ipc://publisher')
        # self.request.connect('tcp://127.0.0.1:5557')
        # self.request.connect('ipc://devicepublisher')
        self.request = ZMQStream(self.request)
        self.request.on_recv(self.callback)

        # self.request.linger = 0
        # self.request.setsockopt(zmq.SUBSCRIBE, b"")

    def subscribe(self, channel_id):
        if type(channel_id) != bytes:
          channel_id = channel_id.encode('ascii')
        self.request.setsockopt(zmq.SUBSCRIBE, channel_id)

    def make_request(self, to, action, msg = None):
      device = Device.select().where(Device.name == to)
      if len(device) > 0:
        device = device.get()

      print("device = ", device.id)
      dr = DeviceRequest(device_id=device.id, state="pending", action=action, payload=msg)
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
        
        self.subscription = subscription
        self.pubsub = ZMQNodePubSub(self.node, self.on_data)
        self.pubsub.connect()
        self.pubsub.subscribe(self.node.identity)
        # self.node.connect("tcp://localhost:5556", "localhost")
        # self.node.add_device("Printer", "/dev/cu.usbserial-14140", subscription)
        # self.node.add_device('camera', '0', subscription)
        
        # self.pubsub.subscribe("")
        print('ws node opened')

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

          if to == "CMD":
            if action == "ADD":
              kind = content.get("kind")
              name = content.get("name")
              res = self.node.add_device(kind, name)
              print(res, flush=True)
              self.write_message(res, binary=True)
          elif action == 'SUB':
            self.pubsub.subscribe(to)
          else:

            res = self.pubsub.make_request(to, action, content)
        except Exception as err:
          print("EXCEPTION", flush=True)
          print(str(err), flush=True)
          self.write_message({"error": str(err)})
            # if action:
            #   data = [self.node.identity, to.encode('ascii'), action.encode('ascii'), innermsg.encode("ascii")]
            # else:
            #   data = [self.node.identity, to.encode('ascii'), innermsg.encode("ascii")]

            # self.router
            # self.pubsub.socket.send_multipart(data)
          # if (len(msg) > 2):
          #   ["DEVICENAME", "COMMAND", "RECORD"]


          # print(msg, flush=True)
          
          # print(innermsg)
          # self.pubsub.request.send_multipart([b'toyou', b'blah', b'tada'])
          # self.pubsub.socket.send_multipart([b'', b'blah', b'tada'])
          
          # to = msg.pop('to') or 0


        #   action  = msg.get('subscribe')
          
        #   if action:
        #     res = self.pubsub.subscribe(action)
        #     print(f'Subscription= {str(res)}', flush=True)
        #     self.write_message({"message": "subscribed to it"})

          # params  = {k:v for k,v in filter(lambda t: t[0] != "action", msg.items())}
      
          # if not action:
          #   self.write_error({'error': 'no action provided'})
          #   return

          # method = getattr(self, action)

          # if not method:
          #   self.write_error({'error': f'no action {action} found'})
          #   return

          # if len(params) > 0:
          #   await method(**params)
          # else:
          #   await method()
        
    
    def on_close(self):
        print('ws closed')

    def on_data(self, data):
        print("ON DATA", flush=True)
        print(data, flush=True)
        node_identifier, request_id, msg = data
        print(node_identifier, flush=True)
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

        self.write_message(msg, binary=True)
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
      (r"/printers",  PrinterResource),
      (r"/ports",     PortsResource),
      (r"/serial",    SerialResource),
      (r"/node/(.*)",   NodeSocket, dict(node=self.node_server)),
      # (r"/webcam/(.*)",   StreamHandler),
      (r"/app/(.*)",  StaticFileHandler, dict(path = STATIC_FOLDER)),
    ], **settings)

    return _app

  def start(self):
    print("Starting api server...")

    # server = tornado.httpserver.HTTPServer(self.app)
    # server.bind(5000)
    # server.start(0)
    self.app.listen(5000)
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()
