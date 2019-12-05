'''
 slice_file.py
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

class SliceFile(BaseModel):
  name            = CharField()
  generated_name  = CharField()
  path            = CharField(unique=True)
  layerkeep_id    = IntegerField(null=True)
  source          = CharField(default="local")

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'name':       self.name,
      'path':       self.path,
      'layerkeep_id':       self.layerkeep_id
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.path
    )

  class Meta:
    table_name = "slice_files"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Printer, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
