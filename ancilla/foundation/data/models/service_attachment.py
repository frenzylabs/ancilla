'''
 printer.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
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
  # name      = CharField(unique=True)  
  settings     = JSONField(default={})
  listeners    = JSONField(default={})
  parent       = ForeignKeyField(Service, column_name='parent_id', index=True, null=False, backref="service_attachments")
  attachment   = ForeignKeyField(Service, column_name='attachment_id', index=True, null=False, backref="attached_services")


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



# DeviceAttachmentProxy.initialize(DeviceAttachment)
