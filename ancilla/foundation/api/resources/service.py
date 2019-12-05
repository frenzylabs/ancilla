'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler
from ...serial  import SerialConnection

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
    #   dict(
    #     baud_rates=SerialConnection.baud_rates(),
    #     ports=SerialConnection.list_ports()
    #   )
    # )

    # self.finish()

  # def get(self, *args, **kwargs):
  #   # pr = Printer.select().dicts().get()
  #   # print(pr)
  #   # for printer in Printer.select():
  #   #   print(printer.__data__.get("created_at"))
  #   #   print(printer.json, flush=True)
  #   #   # printer.de
  #   for device in Device.select():
  #     ModelCls = getattr(importlib.import_module("ancilla.foundation.data.models"), device.device_type)
  #       specific = ModelCls(self.ctx, identifier)
  #       prefetch


  #   self.write(
  #     {'devices': [device.json for device in Device.select()]}
  #   )
    