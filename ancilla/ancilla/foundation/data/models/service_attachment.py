'''
 service_attachment.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 11/23/19
 Copyright 2019 FrenzyLabs, LLC.
'''

from .base import BaseModel
from .service import Service

from peewee import (
  CharField,
  TextField,
  ForeignKeyField,
  DeferredForeignKey,
  Proxy
)

from playhouse.sqlite_ext import JSONField

class ServiceAttachment(BaseModel):    
  settings     = JSONField(default=dict)
  listeners    = JSONField(default=dict)
  parent       = ForeignKeyField(Service, on_delete="CASCADE", column_name='parent_id', index=True, null=False, backref="service_attachments")
  attachment   = ForeignKeyField(Service, on_delete="CASCADE", column_name='attachment_id', index=True, null=False, backref="attached_to")


  @property
  def serialize(self):
    return {
      'id':         self.id,
      'settings':   self.settings,
      'listeners':  self.listeners,
      'parent_id':   self.parent_id,
      'attachment_id':   self.attachment_id
    }


  def __repr__(self):
    return "{}, {}, {}, {}".format(
      self.id, 
      self.settings, 
      self.listeners,
      self.parent_id
    )

  

  class Meta:
    table_name = "service_attachments"

