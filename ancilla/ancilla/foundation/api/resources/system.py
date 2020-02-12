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
    print(f'System reques parms = {self.params.get("wifi")}')
    newconfig = {}
    if (len(args) > 0):
      if args[0] == "/restart":
          newconfig["restart_ancilla"] = int(time.time())
      elif args[0] == "/reboot":
          newconfig["reboot"] = int(time.time())
      elif args[0] == "/wifi":
          if "wifi" in self.params:
            newconfig["wifion"] = self.params.get("wifi")

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

  async def get(self, *args):
    # if (len(args) > 0):
    #   if args[0] == "/network_connected":
    #     self.write(self.network_connected())
    #     return

    config_path = "/".join([Env.ancilla, "config.json"])
    configdata = {}
    with open(config_path, "r") as f:
        configdata = json.load(f)
    self.write({"data": configdata})



  # def network_connected(self):
  #   import subprocess
  #   try:
  #     res = subprocess.check_output(['ping', '-c', '1', '-W', '1',  '8.8.8.8'])
  #     if res:
  #       return {"status": True}
  #   except Exception as e:
  #     print(f"Network Excepton = {str(e)}")
  #   return {"status": False}

