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

class DiscoveryResource(BaseHandler):
  def initialize(self, beacon):
    self.beacon = beacon

  def get(self, *args):
    # print("INSIDE GET Discvoer", self.beacon)
    # print(f"INSIDE GET beacon {self.beacon.type}, {self.beacon.name}")
    # _broadcast  = self.beacon.conf.get_service_info(self.beacon.type, "{}.{}".format(self.beacon.name, self.beacon.type))
    # print(f"INSIDE GET Broadcast {_broadcast}")
    # _addrs      = [("%s" % socket.inet_ntoa(a)) for a in _broadcast.addresses]
    # print(f"INSIDE GET Broadcast {_addrs}")
    # print(f"Get Services {self.beacon.listener.myservices}")
    self.write(
      {'nodes': self.beacon.listener.myservices}
    )

  # def post(self, *args, **kwargs):
  #   kind = self.params.get('kind', None)
  #   name = self.params.get('name', None)
  #   self.node.add_device(kind, name)

  #   self.write("success")
    
