'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from tornado.web    import RequestHandler
from .base      import BaseHandler
from ...serial  import SerialConnection
import re
import pickle 
import numpy as np
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop
import asyncio
import cv2

numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts


class ZMQCameraPubSub(object):

    def __init__(self, callback):
        self.callback = callback
        # self.subscribe_callback = subscribe_callback
        # self.node = node

    def connect(self):
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.subscriber.connect('ipc://publisher')
        # self.request.connect('tcp://127.0.0.1:5557')
        # self.request.connect('ipc://devicepublisher')
        self.subscriber = ZMQStream(self.subscriber)
        self.subscriber.on_recv(self.callback)
        

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

class WebcamHandler(RequestHandler):
    def initialize(self, node):
      self.node = node

    # @gen.coroutine
    def on_message(self, data):
      # print("ON MESSAGE: ", flush=True)
      # topic, msg = yield self.socket.request.recv_multipart()
      topic, framenum, msg = data
      fnum = int(framenum.decode('utf-8'))
      # print("fRAME = ", fnum)
      frame = pickle.loads(msg)
      frame = cv2.flip(frame, 1)

      x = cv2.resize(frame, dsize=(640, 480), interpolation=cv2.INTER_CUBIC)
      # print(x.shape)

      x = x.astype(np.uint8)
      (flag, encodedImage) = cv2.imencode(".jpg", x)

      self.write(b'--frame\r\n')
      self.write(b'Content-Type: image/jpeg\r\n\r\n')
      self.write(encodedImage.tobytes())
      self.write(b'\r\n\r\n')
      IOLoop.current().add_callback(self.flushit)

    
    async def flushit(self):
      # print("FLUSHING WRITE", flush=True)
      await self.flush()
    

    # @gen.coroutine
    async def camera_frame(self, subscription):
        """ Sleep without blocking the IOLoop. """        
        # # self.fourcc = cv2.VideoWriter_fourcc(*'MP42')
        # self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        # # self.fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        # videosize = (640,480)
        # self.vidout = cv2.VideoWriter('output.mov', cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)
        # # self.vidout = cv2.VideoWriter('output.mpeg', self.fourcc, 24.0, (640,480))
        self.pubsub = ZMQCameraPubSub(callback=self.on_message)
        self.pubsub.connect()
        self.pubsub.subscribe(subscription)
        # IOLoop.current().add_callback(self.flushit)
        while True:
          await asyncio.sleep(1)


    async def get(self, *args):
        print("HI THERE", flush=True)
        # def open(self, *args, **kwargs):
        subscription = ""
        if (len(args) > 0):
          subscription = args[0]
        
        print(f"Camera SUBSCRIBE = {subscription}", flush=True)
        


        
        self.subscription = subscription
        # self.pubsub = ZMQNodePubSub(self.node, self.on_data, self.subscribe_callback)
        

        self.set_header('Cache-Control',
        'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        self.set_header('Connection', 'close')
        # self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary=-boundarydonotcross')
        self.set_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        # mimetype='multipart/x-mixed-replace; boundary=frame')
        
        print("Start request")
        resp = self.node.request([subscription.encode('ascii'), b'get_state', b''])
        jresp = json.loads(resp)
        print(f'NODE REQ: {jresp}', flush=True)
        if jresp.get("running") != True:          
          self.write_error(400, errors=jresp)
          self.flush()
        else:
          await self.camera_frame(self.subscription)




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