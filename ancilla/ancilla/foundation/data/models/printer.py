'''
 printer.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base import BaseModel
from .service import Service

from peewee import (
  CharField,
  TextField,
  ForeignKeyField,
  IntegerField
)

class Printer(BaseModel):
  name      = CharField(unique=True)
  port      = CharField()
  baud_rate = CharField()
  model     = CharField(null=True)
  description = CharField(null=True)

  service    = ForeignKeyField(Service, null=True, default=None, on_delete="SET NULL", backref="camera")
  
  layerkeep_id = IntegerField(null=True)

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

  # def device(self):
  #   Device.select().where()
  
  # def save(self, *args, **kwargs):

  #   with self._meta.database.atomic() as transaction:    
  #     try:
  #       if not self.service_id:
  #         # if self.name != 
  #         clsname = self.__class__.__name__
  #         service = Service(name=self.name, class_name=clsname)
  #         service.save()
  #         self.service_id = service.id
  #       else:
  #         if self.name != self.service.name:
  #           self.service.name = self.name
  #           self.service.save()

  #       super().save(*args, **kwargs)  
        
        
  #     except Exception as e:
  #       print(f"Couldn't save model {str(e)}")
  #       # Because this block of code is wrapped with "atomic", a
  #       # new transaction will begin automatically after the call
  #       # to rollback().
  #       transaction.rollback()
  #       error_saving = True

  class Meta:
    table_name = "printers"

# class PrinterLog(BaseModel):
#   content = TextField()
#   printer = ForeignKeyField(Printer, backref='logs')

#   class Meta:
#     table_name = "printer_logs"
