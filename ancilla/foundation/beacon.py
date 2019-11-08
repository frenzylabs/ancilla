'''
 beacon.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/04/19
 Copyright 2019 Wess Cope
'''

import socket

from zeroconf import Zeroconf, ServiceInfo

class Beacon(object):
  conf  = Zeroconf()
  
  def __init__(self, name="ancilla", port=5000, *args, **kwargs):
    self.name = name
    self.port = port
    self.host_name = socket.gethostname() 
    self.host_ip = socket.gethostbyname(self.host_name) 

  @property
  def info(self):
    return ServiceInfo(
      "_{}._tcp.local.".format(self.name),
      "{}._{}._tcp.local.".format(self.name.capitalize(), self.name),
      addresses=[socket.inet_aton(self.host_ip)],
      port=self.port,
      server="{}.local.".format(self.name)
    )

  def register(self):
    self.conf.register_service(self.info)
    
  def update(self):
    self.conf.update_service(self.info)
