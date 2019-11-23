'''
 printer.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base import BaseModel
from .device import Device

from peewee import (
  CharField,
  TextField,
  ForeignKeyField,
  DeferredForeignKey,
  Proxy
)

from playhouse.sqlite_ext import JSONField

class DeviceAttachment(BaseModel):  
  # name      = CharField(unique=True)  
  settings     = JSONField(default={})
  listeners    = JSONField(default={})
  parent       = ForeignKeyField(Device, column_name='parent_id', index=True, null=False, backref="device_attachments")
  attachment   = ForeignKeyField(Device, column_name='attachment_id', index=True, null=False, backref="attachment_devices")


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
    table_name = "device_attachments"



# DeviceAttachmentProxy.initialize(DeviceAttachment)
