'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler
from ...serial  import SerialConnection

class PortsResource(BaseHandler):
  def get(self, *args, **kwargs):
    self.write(
      dict(
        baud_rates=SerialConnection.baud_rates(),
        ports=SerialConnection.list_ports()
      )
    )

    self.finish()
