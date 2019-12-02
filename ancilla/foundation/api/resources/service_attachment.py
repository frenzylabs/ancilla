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
from ...data.models import Service, ServiceAttachment

class ServiceAttachmentResource(BaseHandler):
  def initialize(self, node, **kwargs):
    self.node = node

  def get(self, service_id, *args):
    print("INSIDE GET REQUEST", service_id)
    self.write(
      {'attachments': [da.json for da in ServiceAttachment.select().where(ServiceAttachment.parent_id == service_id)]}
    )

  def post(self, service_id, *args):
    dvc = Service.get_by_id(service_id)
    print("INSIDE POST", *self.params)
    attachment_id = self.params.get('attachment_id', None)
    da = ServiceAttachment(attachment_id=attachment_id, parent_id=service_id)
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
    
