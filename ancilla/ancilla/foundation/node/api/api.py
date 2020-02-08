'''
 api.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
import json

from ...data.models import Service, ServiceAttachment
from ..response import AncillaError


class Api(object):
    
    def __init__(self, service):
        self.service = service                
        self.setup()

    def setup(self, prefix = ""):
      self.service.route(f'{prefix}/settings', 'GET', self.settings)
      self.service.route(f'{prefix}/actions', 'GET', self.actions)
      self.service.route(f'{prefix}/routes', 'GET', self.routes)
      self.service.route(f'{prefix}/events', 'GET', self.events)
      self.service.route(f'{prefix}/attachments/<attachment_id>', 'DELETE', self.delete_attachment)
      self.service.route(f'{prefix}/attachments', 'POST', self.add_attachment)
      self.service.route(f'{prefix}/attachments', 'GET', self.attachments)

    def settings(self, *args):
      return {"settings": self.service.settings.to_json()}

    def routes(self, *args):
      return {"routes": [f"{r}" for r in self.service.routes]}

    def actions(self, *args):      
      return {"actions": self.service.list_actions()}
    
    def events(self, *args):
      # print(f"THE EVENT DICT = {self.service.event_class.event_dict()}", flush=True)
      return {"events": self.service.event_class.list_events()}      

    def delete_attachment(self, request, attachment_id, *args, **kwargs):
      # attachment = self.service.model.service_attachments.where(ServiceAttachment.attachment_id == service_id).first()
      attachment = self.service.model.service_attachments.where(ServiceAttachment.id == attachment_id).first()
      if attachment:
        attachment.delete_instance()        
        return {"sucess": "Removed Attachment"}

      raise AncillaError(404, {"error": "No Attachment Found"})

      
    def add_attachment(self, request, *args):
      service_id = request.params.get("service_id")
      
      res = self.service.model.service_attachments.where(ServiceAttachment.attachment_id == service_id).first()
      if res:
        return {"attachment": res.json}
        
      attachment = Service.get_by_id(service_id)
      sa = ServiceAttachment(parent=self.service.model, attachment=attachment)
      sa.save()
      return {"attachment": sa.json}

    def attachments(self, *args):
      return {"attachments": [a.json for a in self.service.model.service_attachments]}

    def update_attachment(self, request, attachment_id, *args):
      pass

  