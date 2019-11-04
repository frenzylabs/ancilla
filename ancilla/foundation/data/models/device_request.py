'''
 printer.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base import BaseModel

from peewee import (
  CharField,
  TextField,
  IntegerField,
  ForeignKeyField
)

class DeviceRequest(BaseModel):  
  device_id   = IntegerField()
  state       = CharField()
  action      = CharField()
  payload     = CharField(null=True)  

  @property
  def serialize(self):
    return {
      'id':           self.id,
      'device_id':    self.device_id,
      'state':        self.state,
      'action':       self.action,
      'payload':      self.payload
      
    }


  def __repr__(self):
    return "{}, {}, {}, {}, {}".format(
      self.id, 
      self.device_id,
      self.state,
      self.action,
      self.payload,
    )

  class Meta:
    table_name = "device_requests"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Device, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
