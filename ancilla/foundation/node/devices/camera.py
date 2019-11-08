import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
from ..zhelpers import zpipe

import cv2

import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop

from ..zhelpers import zpipe, socket_set_hwm
from ...data.models import Camera as CameraModel
from ..device import Device
from ...env import Env
from ...data.models import DeviceRequest
from .camera_connector import CameraConnector
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback


from ..tasks.device_task import PeriodicTask
# from ..tasks.print_task import PrintTask

# from .middleware import PrinterHandler


    

class Camera(Device):
    connector = None
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time
    state = "IDLE"
    recording = False
    task_queue = Queue()
    # command_queue = CommandQueue()

    def __init__(self, ctx, name, **kwargs):
        self.camera_model = CameraModel.get(CameraModel.name == name)
        
        # self.port = self.record['port']
        # self.baud_rate = self.record['baud_rate']

        
        super().__init__(ctx, name, **kwargs)

        # self.register_data_handlers(PrinterHandler(self))



    def start(self, *args):
      print(f"START Camera {self.identity}", flush=True)
      self.connector = CameraConnector(self.ctx, self.identity, self.camera_model.endpoint)
      # self.connector.start()
    
    def connect(self, *args):
      try:
        # if not self.connector:
        #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
        # else:
        self.connector.open()
        print("Camera Connect", flush=True)
        self.connector.run()
        return {"sent": "Connect"}
      except Exception as e:
        print(f'Exception Open Conn: {str(e)}')
        self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    def stop(self, *args):
      print("Camera Stop", flush=True)
      self.connector.close()


    def close(self, *args):
      print("Camera Close", flush=True)
      self.connector.close()


    def pause(self, *args):
      if self.state == "printing":
        self.state = "paused"
      return {"state": self.state}

    def periodic(self, request_id, data):
      try:
        res = data.decode('utf-8')
        payload = json.loads(res)
        name = payload.get("name") or "PeriodicTask"
        method = payload.get("method")
        timeinterval = payload.get("interval")
        pt = PeriodicTask(name, request_id, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(self._process_tasks)

      except Exception as e:
        print(f"Cant periodic task {str(e)}", flush=True)


    def start_print(self, request_id, data):
      try:
        res = data.decode('utf-8')
        payload = json.loads(res)
        name = payload.get("name") or "PeriodicTask"
        method = payload.get("method")
        pt = PrintTask(name, request_id, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(partial(self._process_tasks))

      except Exception as e:
        print(f"Cant periodic task {str(e)}", flush=True)

      return {"queued": "success"}


    def publish_request(self, request):
      rj = json.dumps(request.json).encode('ascii')
      self.pusher.send_multipart([self.identity+b'.request', b'request', rj])
            
              



# class CameraConnector(object):
#   def __init__(self, ident, pub_endpoint, endpoint, baudrate, pipe, debug = True):
#     self.publisher_endpoint = pub_endpoint
#     self.identity = ident
#     self.serial_endpoint = endpoint

#     ctx = zmq.Context.instance()   
#     socket = ctx.socket(zmq.PUB)
#     socket.bind(f'ipc://{self.identity}')

#     capture = cv2.VideoCapture('rtsp://192.168.1.64/1')
#     # socket.bind("tcp://*:5555")
#     self.video = cv2.VideoCapture(0)



# class CameraDevice(object):
#     endpoint = None         # Server identity/endpoint
#     identity = None
#     alive = True            # 1 if known to be alive
#     ping_at = 0             # Next ping at this time
#     expires = 0             # Expires at this time

#     def __init__(self, endpoint, identity = None):      
#         self.endpoint = endpoint
#         if identity == None: 
#           identity = endpoint
#         self.identity = identity

#         self.alive = True        
#         self.ping_at = time.time() + 1e-3*PING_INTERVAL
#         self.expires = time.time() + 1e-3*SERVER_TTL

#         self.ctx = zmq.Context()
#         self.pipe, peer = zpipe(self.ctx)        
#         # self.server = threading.Thread(target=run_server, args=(self.ctx,))
#         # self.server.daemon = True
#         # self.server.start()
#         self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer,))
#         self.agent.daemon = True
#         self.agent.start()

#     def run_server(self, ctx, pipe):
#       print("RUN Camera SERVER", flush=True)
#       publisher = ctx.socket(zmq.PUB)
#       publisher.bind(f'ipc://devicepublisher')
#       # publisher.connect("ipc://collector")
#       # publisher.send_multipart([b'ender3', b'hello there'])
#       # if self.endpoint
#       # 'rtsp://192.168.1.64/1'
#       endpoint = self.endpoint.decode('utf-8')
#       if endpoint == '0':
#         endpoint = 0
#       video = cv2.VideoCapture(endpoint)
#       # camera = CameraConn(self.identity, "ipc://collector", self.endpoint.decode("utf-8"), self.baudrate, pipe)
#       i=0
#       # topic = 'camera_frame'
#       while self.alive:
#           i += 1
#           ret, frame = video.read()
#           # frame = video.read()
#           print("HI", ret)

#           # publisher.send_multipart([self.identity, frame])
#           publisher.send(self.identity, zmq.SNDMORE)
#           publisher.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
#           publisher.send_pyobj(frame)
#           # time.sleep(2)
#           print('Sent frame {}'.format(i))

#       # while self.alive:
#       #   try:
#       #       cmd, data = pipe.recv_multipart()
#       #       print("Received Data: ", data)
#       #       if data:
#       #         serial_conn.serial.write(data+b'\n')
#       #   except Exception as msg:
#       #       print('{}'.format(msg))            
#       #       # probably got disconnected
#       #       break


#     def send(self, msg):
#       print(msg)    