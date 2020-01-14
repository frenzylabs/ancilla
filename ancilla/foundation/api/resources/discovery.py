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
    # info = zeroconf.get_service_info(type, name)
    # addresses = [("%s" % socket.inet_ntoa(a)) for a in info.addresses]
    # services = map(lambda s: self.beacon.sb.services
    # services = {}
    # for name in self.beacon.sb.services:
    #   s = self.beacon.sb.services[name]
    #   print(s)
    #   print(f"name: {s.name}")
      # print(s.addresses)

      # addresses = [("%s" % socket.inet_ntoa(a)) for a in s.addresses]
      # services[name] = {"addresses": addresses, "port": s.port, "server": s.server}
    
    # self.myservices[f"{name}"] = {"addresses": addresses, "port": info.port, "server": info.server}

    self.write(
      {'nodes': self.beacon.listener.myservices}
    )

  # def post(self, *args, **kwargs):
  #   kind = self.params.get('kind', None)
  #   name = self.params.get('name', None)
  #   self.node.add_device(kind, name)

  #   self.write("success")
    
