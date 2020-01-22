'''
 service.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import json

from .base      import BaseHandler

import time

import asyncio
import functools
import requests
from ...env import Env

class SystemResource(BaseHandler):
  def initialize(self, node):
    self.node = node

  async def post(self, *args):
    newconfig = {}
    if (len(args) > 0):
      if args[0] == "/restart":
          newconfig["restart_ancilla"] = int(time.time())
      elif args[0] == "/reboot":
          newconfig["reboot"] = int(time.time())

    configdata = None
    config_path = "/".join([Env.ancilla, "config.json"])
    try:
      with open(config_path, "r") as f:
        configdata = json.load(f)
        systemconfig = configdata.get("system") or {}
        systemconfig.update(newconfig)
        configdata.update({"system": systemconfig})
      if configdata:
        with open(config_path, 'w') as json_file:
          json.dump(configdata, json_file, indent = 4) 
        self.write({"data": "true"})
      else:
        self.set_status(400)
        self.write({"errors": ["No config path"] }) 
    except Exception as e:
      self.set_status(400)
      self.write({"errors": [str(resp.exception())] }) 

