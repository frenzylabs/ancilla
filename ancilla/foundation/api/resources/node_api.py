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

# from tornado.escape import json_decode
from tornado.escape import utf8, _unicode
from tornado.util import unicode_type
from typing import (
    Dict,
    Any,
    Union
)

from ...node.router import RouterError

from ...utils import ServiceJsonEncoder
from ...node.response import AncillaResponse

# from ..utils import ServiceJsonEncoder

class NodeApiHandler(BaseHandler):
    def initialize(self, node):
      self.node = node
          
    def prepare(self):
      super().prepare()
      myparams = { k: self.get_argument(k) for k in self.request.arguments } 
      self.params.update(myparams)
      print(f"PREPARE {self.request.method}", flush=True)
      self.environ = {"REQUEST_METHOD": self.request.method.upper(), "PATH": self.request.path, "params": self.params}
      if self.request.files:
        self.environ["files"] = self.request.files

    def write(self, chunk: Union[str, bytes, dict]) -> None:
      if self._finished:
          raise RuntimeError("Cannot write() after finish()")
      if not isinstance(chunk, (bytes, unicode_type, dict)):
          message = "write() only accepts bytes, unicode, and dict objects"
          if isinstance(chunk, list):
              message += (
                  ". Lists not accepted for security reasons; see "
                  + "http://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.write"  # noqa: E501
              )
          raise TypeError(message)
      if isinstance(chunk, dict):
          # chunk = escape.json_encode(chunk)
          chunk = json.dumps(chunk, cls=ServiceJsonEncoder)
          self.set_header("Content-Type", "application/json; charset=UTF-8")
      chunk = utf8(chunk)
      self._write_buffer.append(chunk)
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
          resp = await self.node(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"DELETE REPONSE= {resp}", flush=True)
          self.write(resp)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_status(e.status_code)
          self.write(e.body)
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
          resp = await self.node(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"PATCH REPONSE= {resp}", flush=True)
          self.set_status(resp.status_code)
          self.write(resp.body)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_status(e.status_code)
          self.write(e.body)
        except Exception as e:
          print(f"postexception = {e}", flush=True)          
        finally:
          self.finish()

    async def post(self, *args):
        print("Start post request", self.request)
        try:
          # resp = await self.test()
          resp = await self.node(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"POST REPONSE= {resp}", flush=True)
          self.set_status(resp.status_code)
          self.write(resp.body)
          # self.write(resp)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_status(e.status_code)
          self.write(e.body)
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
        print(f"self.envrion= {self.environ}", flush=True)
        try:
          # resp = await self.test()
          resp = await self.node(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"REPONSE= {resp}", flush=True)
          self.set_status(resp.status_code)
          self.write(resp.body)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_status(e.status_code)
          self.write(e.body)
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


