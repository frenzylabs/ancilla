'''
 device.py
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

class Device(BaseModel):
  name          = CharField()
  device_type   = CharField()

  @property
  def serialize(self):
    return {
      'id':           self.id,
      'name':         self.name,
      'device_type':  self.device_type,
      'specific': self.specific
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.device_type
    )

  class Meta:
    table_name = "devices"
