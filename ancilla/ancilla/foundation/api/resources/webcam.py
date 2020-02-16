'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from tornado.web    import RequestHandler
from .base      import BaseHandler

from ...data.models import Service
from ...node.response import AncillaResponse

import re
import pickle 

import zmq
from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop
import asyncio
import cv2
import datetime
import time
import numpy as np
import random
import string
import gc

numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts




class ZMQCameraPubSub(object):

    def __init__(self, callback):
        self.callback = callback
        self.name = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))


    def connect(self, stream):
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.setsockopt(zmq.RCVHWM, 1)
        self.subscriber.setsockopt(zmq.RCVBUF, 1*1024)
        self.subscriber.setsockopt( zmq.LINGER, 0 )
        self.subscriber.connect(stream)
        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.on_recv(self.callback, copy=False)
        
        
        # self.request.linger = 0
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, self.name.encode('ascii'))


    def close(self):
      if self.subscriber:
        self.subscriber.stop_on_recv()
        self.subscriber.close()
        self.subscriber = None

    def subscribe(self, to, topic=''):
      subscribeto = to
      if len(topic) > 0:
        subscribeto = f"{subscribeto}.{topic}"
      subscribeto = subscribeto.encode('ascii')

      self.subscriber.setsockopt(zmq.SUBSCRIBE, subscribeto)
    
    def unsubscribe(self, to, topic=''):
      subscribetopic = to
      if len(topic) > 0:
        subscribetopic = f"{subscribetopic}.{topic}"
      subscribetopic = subscribetopic.encode('ascii')

      self.subscriber.setsockopt(zmq.UNSUBSCRIBE, subscribetopic)    

class WebcamHandler(RequestHandler):
    def initialize(self, node):
      self.node = node
      self.running = True
      self.ready = True
      self.timer = time.time()

    def on_message(self, data):
      if not self.ready or not self.running:
        return

      if len(data) != 3:
        self.ready = False
        self.running = False
        return

      topic, framenum, img = data
      # fnum = int(framenum.decode('utf-8'))
      self.ready = False

      framesize = len(img)

      self.write(b'--frame\r\n')
      self.write(b'Content-Type: image/jpeg\r\n')
      self.write(f"Content-Length: {framesize} \r\n".encode('ascii'))
      self.write(b'\r\n')
      self.write(img.bytes)
      self.write(b'\r\n')
      
      IOLoop.current().add_callback(self.flushit)

    
    async def flushit(self):
      # print("FLUSHING WRITE", flush=True)
      try:
        await self.flush()
        self.ready = True
      except Exception as e:
        print(f"Webcam EXCEPTION {str(e)}")
        self.ready = False
        self.running = False
        self.pubsub.close()

    async def camera_frame(self, stream):
        """ Sleep without blocking the IOLoop. """        

        self.pubsub = ZMQCameraPubSub(callback=self.on_message)
        self.pubsub.connect(stream)

        while self.running:
          await asyncio.sleep(0.05)

    def set_resp_headers(self, resp):
      [self.set_header(k, v) for (k, v) in resp.headers.items()]   

    async def get(self, *args):
        name = ""
        if (len(args) > 0):
          name = args[0]
        
        self.subscription = name + ".events.camera.data_received"

        q = Service.select().where(Service.name == name).limit(1)
        if len(q) > 0:
          service = q.get()
        else:
          self.set_status(404)
          self.write({"error": "Service Not Found"})
          return


        self.set_header('Cache-Control',
        'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')


        environ = {"REQUEST_METHOD": "GET", "PATH": f"/api/services/{service.kind}/{service.id}/video_processor_stream"}
        
        resp = {}
        try: 
          res = await self.node(environ)
          resp = res.body

          # resp = json.loads(resp)
        except AncillaResponse as e:
          print(f"CamAncilla ERRor {e.body}", flush=True)
          self.set_resp_headers(e)
          self.set_status(e.status_code)
          self.write(e.body)

        except Exception as e:
          print(f"Cam ERRor {str(e)}", flush=True)
          resp = {"error": str(e)}
        if not resp.get("stream"):
          self.write_error(400, errors=resp)
          self.flush()
        else:          
          try:
            # self.set_header('Connection', 'close')
            # self.set_header('Connection', 'keep-alive')
            self.set_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.set_header("Expires", datetime.datetime.utcnow())
            self.set_header("Pragma", "no-cache")
            await self.camera_frame(resp.get("stream"))
          except Exception as e:
            print(f"exception {str(e)}", flush=True)
          finally:
            self.pubsub.close()

        self.running = False
        self.ready = False

