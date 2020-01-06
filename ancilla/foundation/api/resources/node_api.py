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
import os

# from tornado.escape import json_decode
from tornado.escape import utf8, _unicode
from tornado.util import unicode_type
from typing import (
    Dict,
    Any,
    Union,
    Iterable
)

from ...node.router import RouterError

from ...utils.service_json_encoder import ServiceJsonEncoder
from ...node.response import AncillaResponse

# from ..utils import ServiceJsonEncoder

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
      self.environ['request.headers'] = self.request.headers

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

    def set_resp_headers(self, resp):
      [self.set_header(k, v) for (k, v) in resp.headers.items()]    

    
    async def delete(self, *args):
        print("Start delete request", self.request)
        try:
          resp = await self.node(self.environ)
          self.set_resp_headers(resp)
          self.set_status(resp.status_code)
          self.write(resp.body)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)    
          self.set_resp_headers(e)   
          self.set_status(e.status_code)
          self.write(e.body)
        except Exception as e:
          print(f"deleteexception = {e}", flush=True)  
          self.set_status(400)
          self.write({"error": str(e)})        
        finally:
          self.finish()

    async def patch(self, *args):
        print("Start patch request", self.request)
        try:
          resp = await self.node(self.environ)

          self.set_resp_headers(resp)
          self.set_status(resp.status_code)
          self.write(resp.body)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_resp_headers(e)
          self.set_status(e.status_code)
          self.write(e.body)
        except Exception as e:
          print(f"postexception = {e}", flush=True)   
          self.set_status(400)
          self.write({"error": str(e)})       
        finally:
          self.finish()

    async def post(self, *args):
        print("Start post request", self.request)
        try:
          # resp = await self.test()
          resp = await self.node(self.environ)
          # resp = await self.node.make_request(self.request)
          # print(f"POST REPONSE= {resp}", flush=True)
          self.set_resp_headers(resp)
          self.set_status(resp.status_code)
          self.write(resp.body)
        except AncillaResponse as e:
          print(f"ancillpostexception = {e}", flush=True)       
          self.set_resp_headers(e)
          self.set_status(e.status_code)
          self.write(e.body)
        except Exception as e:
          print(f"postexception = {e}", flush=True)    
          self.set_status(400)
          self.write({"error": str(e)})      
        finally:
          self.finish()


    async def get(self, *args):
        print("Start get request", self.request)
        # print(f'Query ARgs= {self.request.query_arguments}', flush=True)
        # print(f'Q ARgs= {self.get_query_arguments("q")}', flush=True)
        # for (k, v) in self.request.headers.items():
        #     print(f"RequestHeader: K={k}, v={v} ", flush=True)
        try:
          resp = await self.node(self.environ)
          # for (k, v) in resp.headers.items():
          #   print(f"K={k}, v={v} ", flush=True)
          
          self.set_resp_headers(resp)
          self.set_status(resp.status_code)
          try:
            # iterator = iter(resp.body)
            # if isinstance(resp.body, Iterable):
            # print(f"body = {resp.body}", flush=True)
            # if hasattr(resp.body, '__aiter__'):
            if '__aiter__' in dir(resp.body):
              print("Has aeiter", flush=True)
              
              async for frame in resp.body:
                self.write(frame)
                self.flush()                  
                await asyncio.sleep(0.1)
            else:
              self.write(resp.body)
          except TypeError as e:
              # not iterable
              print(f"Not iterable {str(e)}")
              self.write(resp.body)

          # else:
              # iterable
              # print("maybe iterable")
              # self.finish()
          
        except AncillaResponse as e:
          print(f"ancillgetexception = {e}", flush=True)  
          self.set_resp_headers(e)   
          self.set_status(e.status_code)
          self.write(e.body)
        except Exception as e:
          print(f"getexception = {e}", flush=True)    
          self.set_status(400)
          self.write({"error": str(e)})

        finally:
          self.finish()

