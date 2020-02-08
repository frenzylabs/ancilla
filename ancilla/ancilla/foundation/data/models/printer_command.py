'''
 printer_command.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/05/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel
from .printer import Printer
from .print import Print
from .service import Service

from peewee import (
  CharField,
  TextField,
  IntegerField,
  BooleanField,
  ForeignKeyField
)

from playhouse.sqlite_ext import JSONField


class PrinterCommand(BaseModel):
  sequence    = IntegerField(default=1)
  command     = CharField()
  status      = CharField(default="pending")
  nowait      = BooleanField(default=False)

  response    = JSONField(default=list)

  printer     = ForeignKeyField(Printer, on_delete="CASCADE", related_name="commands", null=True, default=None, backref='commands')
  print       = ForeignKeyField(Print, on_delete="CASCADE", related_name='commands', backref='commands', null=True, default=None)

  parent_id   = IntegerField(default=0)
  parent_type = CharField(null=True)


  def identifier(self):
    return f'{self.id}:{self.parent_id}:{self.command}'

  
  @property
  def serialize(self):
    return {
      'id':         self.id,
      'command':       self.command,
      'status':  self.status,
      'response':  self.response
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.command, 
      self.status
    )

  class Meta:
    table_name = "printer_commands"

