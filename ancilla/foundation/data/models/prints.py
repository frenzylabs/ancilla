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
  ForeignKeyField
)

class Printer(BaseModel):
  name      = CharField(unique=True)
  port      = CharField(unique=True)
  baud_rate = CharField()

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'name':       self.name,
      'baud_rate':  self.baud_rate
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.baud_rate
    )

  class Meta:
    table_name = "printers"

class PrinterLog(BaseModel):
  content = TextField()
  printer = ForeignKeyField(Printer, backref='logs')

  class Meta:
    table_name = "printer_logs"
