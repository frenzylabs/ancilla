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
# import numpy as np
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
        # self.subscribe_callback = subscribe_callback
        # self.node = node

    def connect(self, stream):
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect(stream)
        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.on_recv(self.callback, copy=True)
        
        self.subscriber.setsockopt( zmq.LINGER, 0 )
        # self.request.linger = 0
        self.subscriber.setsockopt(zmq.SUBSCRIBE, b"")
        self.subscriber.setsockopt(zmq.SUBSCRIBE, self.name.encode('ascii'))
        
        
        # print(f'Send publihser')
        # self.publisher.send_multipart([self.name.encode('ascii')])


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
      # print("topic = ", subscribeto)
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
      # print("subtopic= ", subscribetopic)
        # self.request.on_recv(callback)
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
        print("webcam data != 3")
        self.ready = False
        self.running = False
        return

      topic, framenum, img = data
      # fnum = int(framenum.decode('utf-8'))
      self.ready = False

      framesize = len(img)
      # print(f"FRAME SIZE = {framesize}")
      self.write(b'--frame\r\n')
      self.write(b'Content-Type: image/jpeg\r\n')
      self.write(f"Content-Length: {framesize} \r\n".encode('ascii'))
      self.write(b'\r\n')
      self.write(img)
      self.write(b'\r\n')
      
      IOLoop.current().add_callback(self.flushit)

    
    async def flushit(self):
      # print("FLUSHING WRITE", flush=True)
      try:
        await self.flush()
        self.ready = True
        gc.collect()
      except Exception as e:
        print(f"EXCEPTION {str(e)}")
        self.ready = False
        self.running = False
        self.pubsub.close()

    

    # @gen.coroutine
    async def camera_frame(self, stream):
        """ Sleep without blocking the IOLoop. """        
        # # self.fourcc = cv2.VideoWriter_fourcc(*'MP42')
        # self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        # # self.fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        # videosize = (640,480)
        # self.vidout = cv2.VideoWriter('output.mov', cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)
        # # self.vidout = cv2.VideoWriter('output.mpeg', self.fourcc, 24.0, (640,480))
        self.pubsub = ZMQCameraPubSub(callback=self.on_message)
        self.pubsub.connect(stream)
        # self.pubsub.subscribe(subscription)
        # "events.camera')
        # IOLoop.current().add_callback(self.flushit)
        while self.running:
          await asyncio.sleep(1.0)

    def set_resp_headers(self, resp):
      [self.set_header(k, v) for (k, v) in resp.headers.items()]   

    async def get(self, *args):
        # def open(self, *args, **kwargs):
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

        # print("Start Camera request", flush=True)

        # environ = {"REQUEST_METHOD": "GET", "PATH": f"/api/services/{service.kind}/{service.id}/state"}
        environ = {"REQUEST_METHOD": "GET", "PATH": f"/api/services/{service.kind}/{service.id}/video_processor_stream"}
        
        # resp = self.node.device_request(payload)
        resp = {}
        try: 
          res = await self.node(environ)
          resp = res.body
          print(resp, flush=True)

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


      # fnum = int.from_bytes(frame_num, byteorder='big')
      
      # image = frame.array
      # cv2.imshow("Frame", image)
      # key = cv2.waitKey(1) & 0xFF
      
      # source = cv2.imdecode(img, 1)
      # cv2.imshow("Stream", source)
      # cv2.waitKey(1)
      # cv2.imshow('image',frame)
      # cv2.waitKey(0)
      # cv2.imshow('frame',frame)
      # img = cv2.imencode('.jpg', frame)[1].tobytes()
      # cv2.imshow('video', frame)
      # cv2.waitKey(1)
      # print(frame.shape)
      # x = frame.reshape(480, 640, 3)
      

      #Separated the channels in my new image
      # x = frame.shape[0]
      # y = frame.shape[1]
      # z = frame.shape[2]
      # new_image_red, new_image_green, new_image_blue = new_image

      #Stacked the channels
      # new_rgb = np.dstack([x, y, z, 1])
      # print(frame)
      # cv2.imshow('image', x)


# video = cv2.VideoCapture(0)

# frame_width = int(video.get(3))
# frame_height = int(video.get(4))
# videosize = (frame_width,frame_height)
# videosize = (640,480)
# videosize = (1028,720)
# # out = cv2.VideoWriter('output.avi',cv2.VideoWriter_fourcc('M','J','P','G'), 29, videosize)
# out = cv2.VideoWriter('output.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)

# i = 120
# while i > 0:
#   i = i - 1
#   ret, frame = video.read()
#   if ret == True: 
#     x = cv2.resize(frame, dsize=videosize, interpolation=cv2.INTER_CUBIC)
#     out.write(x)




# img_array = []
# fps = 15
# capSize = (1028,720) # this is the size of my source video
# fourcc = cv2.cv.CV_FOURCC('m', 'p', '4', 'v') # note the lower case
# self.vout = cv2.VideoWriter()
# success = self.vout.open('output.mov',fourcc,fps,capSize,True) 

# for filename in glob.glob('C:/New folder/Images/*.jpg'):
#     img = cv2.imread(filename)
#     height, width, layers = img.shape
#     size = (width,height)
#     img_array.append(img)
 
#     out = cv2.VideoWriter('output.mpeg', self.fourcc, 24.0, (640,480))
#     out = cv2.VideoWriter('output.avi', cv2.VideoWriter_fourcc(*'MP42'), 15.0, (640,480))
# out = cv2.VideoWriter('output3.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)    
# # for filename in glob.glob('images/*.jpg')
# for filename in sorted(glob.glob(f'images/*.jpg'), key=numericalSort):
#   img = cv2.imread(filename)
#   out.write(img)
  
#   height, width, layers = img.shape
#   size = (width,height)
#   img_array.append(img)

#   img = cv2.imread(filename)
#       out.write(img)

# for i in range(len(img_array)):
#     out.write(img_array[i])

#     out.release()
      # cv2.waitKey(1)

      

      # cv2.imwrite(filename = f"images/chair{fnum}.jpg", img = x)
  
      # x = frame.shape[0]
      # y = frame.shape[1]
      # z = frame.shape[2]
      # x = frame.reshape(480, 640, 3)
      # if fnum < 500:
      #   self.vidout.write(x)
      # else:
      #   if self.vidout.isOpened():
      #     self.vidout.release()

      # self.vidout.write(img.encode('ascii'))
      # img = (b'--frame\r\n'
      #           b'Content-Type: image/png\r\n\r\n' + x + b'\r\n\r\n')
      

      # self.flush()            