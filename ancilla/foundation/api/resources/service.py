'''
 service.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import json

from .base      import BaseHandler

import importlib
from ...data.models import Service

class ServiceResource(BaseHandler):
  def initialize(self, node):
    self.node = node

  def get(self, *args):
    # print("INSIDE GET REQUEST", device_id)
    self.write(
      {'services': [da.json for da in Service.select()]}
    )

  def post(self, *args, **kwargs):
    kind = self.params.get('kind', None)
    name = self.params.get('name', None)
    self.node.add_device(kind, name)

    self.write("success")
    
