'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler
from ...serial  import SerialConnection

class DevicesResource(BaseHandler):
  def initialize(self, node):
    self.node = node

  def post(self, *args, **kwargs):
    kind = self.params.get('kind', None)
    name = self.params.get('name', None)
    self.node.add_device(kind, name)

    self.write("success")
    #   dict(
    #     baud_rates=SerialConnection.baud_rates(),
    #     ports=SerialConnection.list_ports()
    #   )
    # )

    self.finish()
