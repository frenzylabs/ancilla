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
import atexit

# Local imports
from ..env import Env

# Resources
from .resources import (
  FileResource,
  PrinterResource,
  PortsResource,
  DocumentResource,
  CameraResource,
  WebcamHandler,
  ServiceResource,
  PrintResource,
  ServiceAttachmentResource,
  LayerkeepResource,
  WifiResource,
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

# import h5py
from datetime import datetime




class ZMQNodePubSub(object):

    def __init__(self, node, request_callback, subscribe_callback):

        self.callback = request_callback
        self.subscribe_callback = subscribe_callback
        self.node = node

    def connect(self):
        # print("Node PUbsub connect", flush=True)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.ROUTER)
        # url_worker = "ipc://backend.ipc"
        # url_client = "inproc://frontend"
        # self.socket.connect('tcp://127.0.0.1:5560')
        self.socket.connect('tcp://127.0.0.1:5556')
        # self.socket.connect(url_client)
        self.stream = ZMQStream(self.socket)
        self.stream.setsockopt( zmq.LINGER, 0 )
        self.stream.on_recv(self.callback)

        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect('ipc://publisher')
        # self.request.connect('tcp://127.0.0.1:5557')
        # self.request.connect('ipc://devicepublisher')
        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.setsockopt( zmq.LINGER, 0 )
        # self.subscriber.setsockopt( ZMQ:IMMEDIATE)
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
      # if msg and type(msg) == dict:
      #   msg = json.dumps(msg)
        
      kind, *cmds = action.split(".")
      method = action
      if len(cmds) > 0:
        method = cmds[0]

      wrapped = {"data": msg}
      
      return self.node.run_action(method, wrapped, target) 
      
      # response = [to+".request"]
      # if to == "":
      #     payload = [method.encode('ascii')]
      #     if msg:
      #       payload.append(msg.encode('ascii'))
      #     resp = self.node.request(payload)
      #     try: 
      #       resp = json.loads(resp)
      #     except:
      #       pass
      #     response.append(resp)
      #     return resp

      # if kind == "REQUEST":
      #     payload = [to.encode('ascii'), method.encode('ascii')]
      #     if msg:
      #       payload.append(msg.encode('ascii'))
      #     resp = self.node.device_request(payload)
      #     try: 
      #       resp = json.loads(resp)
      #     except:
      #       pass
      #     response.append(resp)
      #     # return resp
      # else:
      #   if to != "":
      #     device = Service.select().where(Service.name == to)
      #     if len(device) > 0:
      #       device = device.get()
      #     else:
      #       raise Exception(f"No Device With Name {to}")

      #     # dr = DeviceRequest(device_id=device.id, status="pending", action=method, payload=msg)
      #     # dr.save()

      #     # print(dr, flush=True)

      #     # payload = [self.node.identity, to.encode('ascii'), action.encode('ascii')]
      #     # if msg:
      #     #   payload.append(msg.encode('ascii'))
          
      #     print("payload = ", payload)
      #     return self.node.run_action(method, msg, to)     

          # self.socket.send_multipart(payload)
          # response.append({"status": "pending", "request": dr.json})
          # return [to + ".request", {"status": "pending", "request": dr.json}
          
      # return response
          

      # if to == "":
      #   action == "REQUEST"
        
      #       resp = self.node.request([method.encode('ascii'), msg.encode('ascii')])
      #       return resp
      #   elif kind == "DEVICE_REQUEST":

      #   self.node.make_request()
      #   resp = self.node.request([subscription.encode('ascii'), b'get_state', b''])
      #   return json.loads(resp)
      # device = Device.select().where(Device.name == to)
      # if len(device) > 0:
      #   device = device.get()
      # else:
      #   raise Exception(f"No Device With Name {to}")
    
      

      # print("device = ", device)
      # dr = DeviceRequest(device_id=device.id, status="pending", action=action, payload=msg)
      # dr.save()
      # print(dr, flush=True)
      # payload = [self.node.identity, f'{dr.id}'.encode('ascii'), to.encode('ascii'), action.encode('ascii')]
      # if msg:
      #   payload.append(msg.encode('ascii'))

      # self.socket.send_multipart(payload)

    # def make_request(self, to, action, msg = None):
    #   device = Device.select().where(Device.name == to)
    #   if len(device) > 0:
    #     device = device.get()
    #   else:
    #     raise Exception(f"No Device With Name {to}")
    
    #   if msg and type(msg) == dict:
    #     msg = json.dumps(msg)

    #   print("device = ", device)
    #   dr = DeviceRequest(device_id=device.id, status="pending", action=action, payload=msg)
    #   dr.save()
    #   print(dr, flush=True)
    #   payload = [self.node.identity, f'{dr.id}'.encode('ascii'), to.encode('ascii'), action.encode('ascii')]
    #   if msg:
    #     payload.append(msg.encode('ascii'))

    #   self.socket.send_multipart(payload)


class NodeSocket(WebSocketHandler):
    def __init__(self, application, request, **kwargs) -> None:
        print(kwargs, flush=True)
        # node = kwargs.get("node")
        self.node = kwargs.pop('node', None)
        self.timer = time.time()
        self.node_connector = ZMQNodePubSub(self.node, self.on_data, self.subscribe_callback)
        self.node_connector.connect()
        self.node_connector.subscribe("notifications")
        super().__init__(application, request, **kwargs)


    def check_origin(self, origin):
      return True

    def open(self, *args, **kwargs):
        subscription = ""
        if (len(args) > 0):
          subscription = args[0]
        
        # print("OPEN NODE SOCKET", flush=True)
        self.subscription = subscription
        
        

        # self.node.connect("tcp://localhost:5556", "localhost")
        # self.node.add_device("Printer", "/dev/cu.usbserial-14140", subscription)
        # self.node.add_device('camera', '0', subscription)
        
        # self.pubsub.subscribe("")
        print('ws node opened')
    
    def subscribe_callback(self, data):
      # print("SUBSCRIBE CB", flush=True)
      # print(f"subcallback, {data}", flush=True)
      if data and len(data) > 2:
        topic, status, msg, *other = data
        # print(topic, flush=True)
        # topic, status, msg = data
        # print(node_identifier, flush=True)
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        senddata = True
        try:
          if (topic.endswith('printer.data_received')):
            if (time.time() - self.timer) > 2:
              self.timer = time.time()
            else:
              senddata = False
          msg = json.loads(msg)
        except Exception as e:
          print(f"SubscribeEXCE = {str(e)}")
          senddata = False
          pass


        if senddata:
          self.write_message(json.dumps([topic, msg]))
        # self.write_message(msg, binary=True)
      # self.write_message("HI")

    def on_message(self, message):
        print(f'MSG: {message}', flush=True)
        
        # self.pubsub.stream.send([b'', '', message.encode("ascii")])
        # self.pubsub.stream.send(message.encode("ascii"))
        # self.pubsub.socket.send_multipart([b'', b'', message.encode("ascii")])
        # self.write_message(message, binary=True)
        to = ""
        try:
          msg     = json.loads(message)
          # print(msg, flush=True)
          target = msg.pop(0)
          action = None
          
          action = msg.pop(0)
          content = None
          if (len(msg) > 0):
            content = msg.pop(0)

          # ['CONTROL', 'ADD|REMOVE' ]
          # ['to', 'SUBSCRIBE', '']
          if action == 'SUB':
            self.node_connector.subscribe(target, content)
          elif action == 'UNSUB':
            self.node_connector.unsubscribe(target, content)
          else:

            res = self.node_connector.make_request(target, action, content)
            print(f"MAKE REQUEST = {res}", flush=True)
            self.write_message(json.dumps(res))
        except Exception as err:
          print("EXCEPTION", flush=True)
          print(str(err), flush=True)
          self.write_message(json.dumps([to+".request", {"error": str(err)}]))

        
    
    def on_close(self):
        self.node_connector.close()
        print('ws closed')

    def on_data(self, data):
        print(f"WS ON DATA {data}", flush=True)
        # print(data, flush=True)
        node_identifier, to, msg = data
        # print(node_identifier, flush=True)
        msg = msg.decode('utf-8')
        try:
          msg = json.loads(msg)
        except:
          pass
        to = to.decode('utf-8')
        self.write_message(json.dumps([to, msg]))

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
    # self.discovery = discovery
    # atexit.register(self.cleanup)

  def cleanup(self):
    print(f"clenup api server")
    self.stop()

  @property
  def app(self):
    settings = {
      'debug' : Env.get('RUN_ENV') == 'DEV',
      'static_path' : STATIC_FOLDER      
    }

    _app = Application([
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
        # # loop = IOLoop.current(instance=True)
    # server = tornado.httpserver.HTTPServer(self.app)
    # server.bind(5000)
    # server.start(0)
    print(f'Server IO LOOP = {IOLoop.current()}', flush=True)
    self.app.listen(5000, **{'max_buffer_size': 10485760000})
    IOLoop.current().start()

  def stop(self):
    IOLoop.current().stop()
