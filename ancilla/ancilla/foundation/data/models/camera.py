'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 11/08/19
 Copyright 2019 FrenzyLabs, LLC.
'''


from .base import BaseModel
from .service import Service

from peewee import (
  CharField,
  TextField,
  ForeignKeyField,
  IntegerField
)

class Camera(BaseModel):
  name      = CharField(unique=True)
  endpoint  = CharField(unique=True)
  # baud_rate = CharField()
  service    = ForeignKeyField(Service, null=True, default=None)
  # service_id = IntegerField(null=True)

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'name':       self.name,
      'endpoint':  self.endpoint
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.endpoint
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
    table_name = "cameras"

