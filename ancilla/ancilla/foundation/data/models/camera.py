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

from playhouse.sqlite_ext import JSONField

class Camera(BaseModel):
  name      = CharField(unique=True)
  endpoint  = CharField(unique=True)
  # baud_rate = CharField()
  service    = ForeignKeyField(Service, null=True, default=None, on_delete="SET NULL", backref="camera")
  settings   = JSONField(default={})
  # service_id = IntegerField(null=True)

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'name':       self.name,
      'endpoint':  self.endpoint,
      'settings':  self.settings
    }


  def __repr__(self):
    return "\\{{}, {}, {}\\}".format(
      self.id, 
      self.name, 
      self.endpoint
    )



  class Meta:
    table_name = "cameras"

