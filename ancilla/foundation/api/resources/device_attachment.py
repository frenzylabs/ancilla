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
from ...data.models import Device, DeviceAttachment

class DeviceAttachmentResource(BaseHandler):
  def initialize(self, node, **kwargs):
    self.node = node

  def get(self, device_id, *args):
    print("INSIDE GET REQUEST", device_id)
    self.write(
      {'attachments': [da.json for da in DeviceAttachment.select().where(DeviceAttachment.parent_id == device_id)]}
    )

  def post(self, device_id, *args):
    dvc = Device.get_by_id(device_id)
    print("INSIDE POST", *self.params)
    attachment_id = self.params.get('attachment_id', None)
    da = DeviceAttachment(attachment_id=attachment_id, parent_id=device_id)
    da.save()

    
    # self.node.add_device(kind, name)

    self.write({"attachment": da})
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
    
