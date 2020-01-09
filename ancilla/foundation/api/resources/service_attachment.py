'''
 service_attachment.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import json

from .base      import BaseHandler

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


    self.write({"attachment": da})

