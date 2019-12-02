'''
 printer_command.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/05/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel
from .device import Device
# from .device_request import DeviceRequest
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
  # response   = TextField(default="")
  response    = JSONField(default=[])
  # printer     = ForeignKeyField(Printer, backref='commands')
  printer     = ForeignKeyField(Printer, on_delete="CASCADE", related_name="commands", null=True, default=None, backref='commands')
  print = ForeignKeyField(Print, related_name='commands', null=True, default=None)
  # printer_id  = IntegerField(index=True)
  # request    = ForeignKeyField(DeviceRequest, backref='commands')
  parent_id   = IntegerField(default=0)
  parent_type = CharField(null=True)


  # def __init__(self, request_id, num, data):
  #   self.request_id = request_id
  #   self.num = num
  #   self.data = data
  #   self.id = f'{request_id}:{num}'
  #   self.expiry = time.time() + 10000
  #   self.status = 'pending'
  #   self.response = []

  def identifier(self):
    return f'{self.parent_id}:{self.command}'

  
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

  # def device(self):
  #   Device.select().where()
  
  # def save(self, *args, **kwargs):

  #   with self._meta.database.atomic() as transaction:    
  #     try:
  #       if not self.device_id:
  #         # if self.name != 
  #         clsname = self.__class__.__name__
  #         device = Device(name=self.name, device_type=clsname)
  #         device.save()
  #         self.device_id = device.id
  #       else:
  #         if self.name != self.device.name:
  #           self.device.name = self.name
  #           self.device.save()

  #       super().save(*args, **kwargs)  
        
        
  #     except Exception as e:
  #       print(f"Couldn't save model {str(e)}")
  #       # Because this block of code is wrapped with "atomic", a
  #       # new transaction will begin automatically after the call
  #       # to rollback().
  #       transaction.rollback()
  #       error_saving = True

  class Meta:
    table_name = "printer_commands"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Printer, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
