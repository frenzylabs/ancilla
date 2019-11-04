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

class Device(BaseModel):
  name          = CharField()
  device_type   = CharField()

  @property
  def serialize(self):
    return {
      'id':           self.id,
      'name':         self.name,
      'device_type':  self.device_type
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.device_type
    )

  class Meta:
    table_name = "devices"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Device, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
