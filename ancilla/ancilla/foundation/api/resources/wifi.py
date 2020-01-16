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

  async def make_request(self, req, content_type = 'json', auth = True, options = {"verify": False}):
      print(f"Requ = {req}")
      prepped = self.session.prepare_request(req)
      if not auth:
        del prepped.headers['Authorization']
      print(f"prepped = {prepped.headers}", flush=True)
      loop = asyncio.get_event_loop()
      makerequest = functools.partial(self.session.send, prepped, **options)

      future = loop.run_in_executor(None, makerequest)

      resp = await future

  async def post(self, *args):
    url = f'http://localhost:8080/connect'    
    req = requests.Request('POST', url, json=self.params)
    resp = await self.make_request(req)
    return resp


  async def get(self, *args):
    # myparams = { k: self.get_argument(k) for k in self.request.arguments }
    # print(f'My params = {myparams}') 
    url = f'http://localhost:8080/status'
    req = requests.Request('GET', url)
    resp = await self.make_request(req)
    return resp

    # self.write(
    #   {'nodes': []}
    # )


