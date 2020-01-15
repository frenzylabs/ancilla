'''
 print_slice.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/05/19
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

class PrintSlice(BaseModel):
  name            = CharField()
  generated_name  = CharField()
  path            = CharField(unique=True)
  source          = CharField(default="local")
  description     = CharField(null=True)
  properties      = JSONField(default={})
  layerkeep_id    = IntegerField(null=True)

  @property
  def serialize(self):
    return {
      'id':           self.id,
      'name':         self.name,
      'path':         self.path,
      'description':  self.description,
      'source':       self.source,
      'properties':   self.properties,
      'layerkeep_id': self.layerkeep_id
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.path
    )

  class Meta:
    table_name = "print_slices"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Printer, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
