'''
 device_request.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/01/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel

from peewee import (
  CharField,
  TextField,
  IntegerField,
  ForeignKeyField
)
from playhouse.sqlite_ext import JSONField

class ServiceRequest(BaseModel):  
  device_id   = IntegerField()
  status      = CharField()
  state       = JSONField(default={})
  action      = CharField()
  payload     = CharField(null=True)  

  @property
  def serialize(self):
    return {
      'id':           self.id,
      'service_id':    self.service_id,
      'status':        self.status,
      'action':       self.action,
      'payload':      self.payload
    }


  def __repr__(self):
    return "{}, {}, {}, {}, {}".format(
      self.id, 
      self.device_id,
      self.status,
      self.action,
      self.payload,
    )

  class Meta:
    table_name = "service_requests"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Device, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
