'''
 print.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/05/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel

from .print_slice import PrintSlice
from .printer import Printer

from peewee import (
  CharField,
  TextField,
  IntegerField,
  ForeignKeyField
)

from playhouse.sqlite_ext import JSONField

class Print(BaseModel):
  name      = CharField(null=True)
  status    = CharField(null=True)
  state     = JSONField(default=dict)
  settings  = JSONField(default=dict)

  printer_snapshot = JSONField(default=dict)
  printer    = ForeignKeyField(Printer, on_delete="CASCADE", backref='prints')
  print_slice    = ForeignKeyField(PrintSlice, on_delete="SET NULL", null=True, backref='prints')

  description = CharField(null=True)
  duration  = IntegerField(default=0)

  layerkeep_id  = IntegerField(null=True)

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'name':       self.name,
      'status':  self.status,
      'state':  self.state,
      'settings':  self.settings,
      'duration': self.duration,
      'description': self.description
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.status
    )

  class Meta:
    table_name = "prints"

