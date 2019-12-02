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
import time

from tornado.escape import json_decode

from ...node.router import RouterError

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

    def close(self):
      self.subscriber.close()

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

class NodeApiHandler(BaseHandler):
    def initialize(self, node):
      self.node = node
      
    def prepare(self):
      super().prepare()
      myparams = { k: self.get_argument(k) for k in self.request.arguments } 
      self.params.update(myparams)
      self.environ = {"REQUEST_METHOD": self.request.method.upper(), "PATH": self.request.path, "params": self.params}
      if self.request.files:
        self.environ["files"] = self.request.files
      # self.running = True
      # self.data = None
      # myctx = zmq.Context()
      # self.socket = myctx.socket(zmq.ROUTER)
      # # self.socket.connect('tcp://127.0.0.1:5556')
      # self.socket.connect(self.node.router_address)

      # self.stream = ZMQStream(self.socket)
      # self.stream.on_recv(self.callback)
      

    # def callback(self, data):
    #   print("INSIDE CALLBACK", flush=True)
    #   print(f"CALLBACK {data}", flush=True)
    #   frm, status, msg, *other = data
    #   self.data = msg
    #   self.running = False
      # if self.ready:
      #   IOLoop.current().add_callback(self.flushit)



    # async def test(self):
      
    #   # socket = self.ctx.socket(zmq.ROUTER)
    #   # self.socket.connect(self.node.router_address)
    #   # self.request.body_arguments
    #   # self.request._get_arguments
    #   # self.get_arguments
      
    #   # socket.send([])
    #   print(f"INSIDE make request = {self.node.router_address}")
    #   print(self.request.body, flush=True)
    #   print(f"self.params= {self.params}")
      
    #   myparams = { k: self.get_argument(k) for k in self.request.arguments } 
    #   print(f"myparams= {myparams}", flush=True)
    #   print(len(myparams))
    #   # if len(myparams) > 0:
    #   self.params.update(myparams)
    #   # if self.params:
    #   #   myparams

    #   print(f"make request arguments = {self.params}")
    #   payload = [self.node.identity, self.request.method.encode('ascii'), self.request.path.encode('ascii'), json.dumps(self.params).encode('ascii')]
    #   print("INSIDE make request payload = ", payload)
    #   # res = await 
    #   # self.socket.send(self.node.identity)
    #   # print("after first send", flush=True)
    #   self.running = True
    #   self.socket.send_multipart(payload)
    #   # self.socket.send_multipart([b'localhost', b'304', b'ender3', b'test'])
    #   t = time.time()
    #   hasNotified = False
    #   while True:
    #       if self.running:
    #         await asyncio.sleep(0.01)
    #         ct = time.time() - t
    #         if ct > 5 and not hasNotified:
    #           hasNotified = True
    #           print("IT's been 5 seconds", flush=True)
    #         if ct > 10:
    #           print("IT's been 10 seconds. cancelling", flush=True)
    #           self.running = False

    #       else:
    #         break
    #   return self.data
    #   print("after sleep")


    async def delete(self, *args):
        print("Start delete request", self.request)
        try:
          # resp = await self.test()
          # file_id = self.get_argument('file_id', None)
          # print(f"Fileid = {file_id}", flush=True)
          # print(f"del env= {self.environ}", flush=True)
          resp = await self.node._handle(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"DELETE REPONSE= {resp}", flush=True)
          self.write(resp)
        except Exception as e:
          print(f"deleteexception = {e}", flush=True)          
        finally:
          self.finish()

        # try:
        #   resp = await self.test()
        #   print(f"delete REPONSE= {resp}", flush=True)
        #   self.write(resp)
        # except Exception as e:
        #   print(f"deleteexception = {e}", flush=True)  

    async def patch(self, *args):
        print("Start patch request", self.request)
        try:
          # resp = await self.test()
          resp = await self.node._handle(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"PATCH REPONSE= {resp}", flush=True)
          self.write(resp)
        except Exception as e:
          print(f"postexception = {e}", flush=True)          
        finally:
          self.finish()

    async def post(self, *args):
        print("Start post request", self.request)
        try:
          # resp = await self.test()
          resp = await self.node._handle(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"POST REPONSE= {resp}", flush=True)
          self.write(resp)
        except Exception as e:
          print(f"postexception = {e}", flush=True)          
        finally:
          self.finish()

        # try:
        #   resp = await self.test()
        #   print(f"post REPONSE= {resp}", flush=True)
        #   self.write(resp)
        # except Exception as e:
        #   print(f"postexception = {e}", flush=True)

    async def get(self, *args):

        
        print("Start request", self.request)
        # payload = [device.encode('ascii'), b'get_state', b'']
        # payload = self.params
        # if msg:
        #   payload.append(msg.encode('ascii'))
        # print(f"INSIDE make request = {self.node.router_address}")
        # print(self.request.body, flush=True)
        print(f"self.envrion= {self.environ}", flush=True)
        

        try:
          # resp = await self.test()
          resp = await self.node._handle(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"REPONSE= {resp}", flush=True)
          self.write(resp)
        except Exception as e:
          print(f"getexception = {e}", flush=True)    
          if type(e) == RouterError:
            self.set_status(e.status)
            self.write({"error": e.body})
          else:
            self.set_status(400)
            self.write({"error": str(e)})

        finally:
          self.finish()
          # self.stream.close()

        # try: 
        #   resp = json.loads(resp).get("resp")
        # except Exception as e:
        #   resp = {"error": str(e)}
          # pass
        # response.append(resp)

        # resp = self.node.request([device.encode('ascii'), b'get_state', b''])
        # jresp = json.loads(resp)
        # print(f'NODE REQ: {resp}', flush=True)
        # if resp.get("running") != True:
        #   self.write_error(400, errors=resp)
        #   self.flush()
        # else:
        #   try:
        #     await self.camera_frame(self.subscription)
        #   except:
        #     print("exception")
          # finally:
          #   self.pubsub.close()


