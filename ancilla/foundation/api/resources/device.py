'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler
from ...serial  import SerialConnection

from ...data.models import Device

class DeviceResource(BaseHandler):
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

  def get(self, *args, **kwargs):
    # pr = Printer.select().dicts().get()
    # print(pr)
    # for printer in Printer.select():
    #   print(printer.__data__.get("created_at"))
    #   print(printer.json, flush=True)
    #   # printer.de

    self.write(
      {'devices': [device.json for device in Device.select()]}
    )
    
