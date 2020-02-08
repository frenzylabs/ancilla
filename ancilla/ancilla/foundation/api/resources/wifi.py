'''
 service.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import json

from .base      import BaseHandler

import importlib
import socket

from ...data.models import Service

import asyncio
import functools
import requests

class WifiResource(BaseHandler):
  def initialize(self, node):
    self.node = node
    self.session = requests.Session()
    self.session.headers.update({"Content-Type" : "application/json", "Accept": "application/json"})
    self.wifi_host = "http://localhost:8080"
    # self.wifi_host = "http://192.168.27.1:8080"

  def handle_response(self, resp):
    try:
      if resp.exception():
        print(f"Resp Exception = {resp.exception()}")
        self.set_status(400)
        self.write({"errors": [str(resp.exception())] })    
      # elif resp.result():
      #   print(f"Resp Result = {resp.result()}")
      #   self.write({"data": resp.result()})
    except Exception as e:
      print(f"HandleExcept = {str(e)}")

  async def make_request(self, req, content_type = 'json', auth = True, options = {"verify": False, "timeout": 10.001}):
      prepped = self.session.prepare_request(req)
      if not auth:
        del prepped.headers['Authorization']
      # print(f"prepped = {prepped.headers}", flush=True)
      loop = asyncio.get_event_loop()
      makerequest = functools.partial(self.session.send, prepped, **options)

      future = loop.run_in_executor(None, makerequest)
      future.add_done_callback(lambda res: self.handle_response(res))

      resp = None
      try:
        resp = await future
      except Exception as ex:
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        msg = template.format(type(ex).__name__, ex.args)
        print(f"{msg}")
      
      return resp

  async def post(self, *args):
    # print(f"WIFI POST = {self.params}")
    url = f'{self.wifi_host}/connect'    
    req = requests.Request('POST', url, json=self.params)
    resp = await self.make_request(req)
    print(f"WIFI POST RESP = {resp}")
    if resp:
      self.set_status(resp.status_code)
      content = {}
      if resp.status_code == 200:
        body = ''
        try:
          body = resp.json()       
        except Exception as e:
          body = resp.text
        content["data"] = body
      else:     
        content["errors"] = [resp.text]
        
      self.write(content)



  async def get(self, *args):
    # myparams = { k: self.get_argument(k) for k in self.request.arguments }
    # print(f'My params = {myparams}') 
    wifipath = "status"
    if (len(args) > 0):
      if args[0] == "/scan":
          wifipath = "scan"


    url = f'{self.wifi_host}/{wifipath}'
    # print(f"GET WIFI URL = {url}")
    req = requests.Request('GET', url)
    resp = await self.make_request(req)

    if resp:
      self.set_status(resp.status_code)
      content = {}
      if resp.status_code == 200:
        body = ''
        try:
          body = resp.json()       
        except Exception as e:
          body = resp.text
        content["data"] = body
      else:     
        content["errors"] = [resp.text]
        
      self.write(content)

