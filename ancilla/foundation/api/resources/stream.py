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

numbers = re.compile(r'(\d+)')
def numericalSort(value):
    parts = numbers.split(value)
    parts[1::2] = map(int, parts[1::2])
    return parts

class StreamHandler(RequestHandler):

    # @gen.coroutine
    def on_message(self, data):
      print("ON MESSAGE: ", flush=True)
      # topic, msg = yield self.socket.request.recv_multipart()
      topic, framenum, msg = data
      fnum = int(framenum.decode('utf-8'))
      # fnum = int.from_bytes(frame_num, byteorder='big')
      print("fRAME = ", fnum)
      frame = pickle.loads(msg)
      # image = frame.array
      # cv2.imshow("Frame", image)
      # key = cv2.waitKey(1) & 0xFF
      frame = cv2.flip(frame, -1)
      # source = cv2.imdecode(img, 1)
      # cv2.imshow("Stream", source)
      # cv2.waitKey(1)
      # cv2.imshow('image',frame)
      # cv2.waitKey(0)
      # cv2.imshow('frame',frame)
      # img = cv2.imencode('.jpg', frame)[1].tobytes()
      # cv2.imshow('video', frame)
      # cv2.waitKey(1)
      print(frame.shape)
      # x = frame.reshape(480, 640, 3)
      x = cv2.resize(frame, dsize=(640, 480), interpolation=cv2.INTER_CUBIC)
      print(x.shape)

      x = x.astype(np.uint8)

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

      (flag, encodedImage) = cv2.imencode(".jpg", x)

      cv2.imwrite(filename = f"images/chair{fnum}.jpg", img = x)
  
      # x = frame.shape[0]
      # y = frame.shape[1]
      # z = frame.shape[2]
      # x = frame.reshape(480, 640, 3)
      if fnum < 500:
        self.vidout.write(x)
      else:
        if self.vidout.isOpened():
          self.vidout.release()

      # self.vidout.write(img.encode('ascii'))
      # img = (b'--frame\r\n'
      #           b'Content-Type: image/png\r\n\r\n' + x + b'\r\n\r\n')
      self.write(b'--frame\r\n')
      self.write(b'Content-Type: image/jpeg\r\n\r\n')
      self.write(encodedImage.tobytes())
      self.write(b'\r\n\r\n')
      # yield img
      # self.write((img))
      IOLoop.current().add_callback(self.flushit)

      # self.flush()
    
    async def flushit(self):
      print("FLUSHING WRITE", flush=True)
      await self.flush()
      

    # @gen.coroutine
    # def handle_data(self):     
      # while True: 
      # self.socket = ZMQCameraPubSub(callback=self.on_message)
      # topic, msg = yield self.socket.request.recv_multipart()
      # frame = pickle.loads(msg)
      
      # img = cv2.imencode('.jpg', frame)[1].tobytes()
      # # # yield img
      # # cv2.imgshow(img)
      # img = (b'--frame\r\n'
      #           b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n\r\n')
      # self.write(img)
      # IOLoop.current().add_callback(self.flushit)
      # await self.flush()

    def test(self):
      print("callback")

    async def testsleep(self):
      await asyncio.sleep(1)
      print('hello')  

    # @gen.coroutine
    async def async_sleep(self, timeout):
        """ Sleep without blocking the IOLoop. """
        # asyncio.Task()
        # await 
        # await asyncio.create_task(self.handle_data)
        # self.fourcc = cv2.VideoWriter_fourcc(*'MP42')
        self.fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        # self.fourcc = cv2.VideoWriter_fourcc(*'DIVX')
        videosize = (640,480)
        self.vidout = cv2.VideoWriter('output.mov',cv2.VideoWriter_fourcc('m','p','4','v'), 29, videosize)
        # self.vidout = cv2.VideoWriter('output.mpeg', self.fourcc, 24.0, (640,480))
        self.socket = ZMQCameraPubSub(callback=self.on_message)
        # IOLoop.current().add_callback(self.flushit)
        while True:
          await self.testsleep()
        # await self.handle_data()
        # await asyncio.create_task(IOLoop.instance().add_timeout(time.time() + timeout, self.test))
        
        # await asyncio.Task(IOLoop.instance().add_timeout, time.time() + timeout)
    
    # @tornado.web.asynchronous
    # @gen.coroutine
    async def get(self, *args):
        print("HI THERE", flush=True)

        self.set_header('Cache-Control',
        'no-store, no-cache, must-revalidate, pre-check=0, post-check=0, max-age=0')
        # self.set_header('Connection', 'close')
        # self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary=-boundarydonotcross')
        self.set_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        # mimetype='multipart/x-mixed-replace; boundary=frame')
        
        print("Start request")
        await self.async_sleep(5)
        # await asyncio.sleep(10)
        print("Okay done now")
        # IOLoop.current().spawn_callback(self.handle_data)
        # await self.handle_data()
        # return response
        # self.ioloop = tornado.ioloop.IOLoop.instance() 

        # self.pipe = self.get_pipe()        
        # self.ioloop.add_handler( self.socket.fileno(), self.async_callback (self.on_message), self.ioloop.READ)

        # context = zmq.Context()
        # socket = context.socket(zmq.SUB)
        # socket.connect('ipc://devicepublisher')      
        # socket.linger = 0
        # socket.setsockopt(zmq.SUBSCRIBE, b"")
        # io_loop = tornado.ioloop.IOLoop.current()
        # callback = functools.partial(connection_ready, sock)
        # io_loop.add_handler(sock.fileno(), callback, io_loop.READ)
        # loop.add_callback(partial(self.on_message(), self.ioloop))
        # self.ioloop.add_callback(lambda: self.handle_data())      
        # while True:
        #   self.handle_data()
        #   yield self.handle_data()
        # yield self.on_message()
        # yield tornado.gen.Task(self.flush)
        # while True:
            # topic, msg = socket.recv_multipart()
            # frame = pickle.loads(msg)

            # if self.get_argument('fd') == "true":
            #     img = cam.get_frame (True)
            # else:
            #     img = cam.get_frame(False)
            # self.write("--boundarydonotcross\n")
            # self.write("Content-type: image/jpeg\r\n")
            # self.write("Content-length: %s\r\n\r\n" % len(frame))
            # img = cv2.imencode('.jpg', frame)[1].tobytes()
            # self.write((img))
            # yield tornado.gen.Task(self.flush)