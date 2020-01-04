'''
 service.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/01/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel
# from .printer import Printer
import re

from peewee import (
  CharField,
  TextField,
  IntegerField
)

from playhouse.sqlite_ext import JSONField


class Service(BaseModel):
  name             = CharField()
  kind             = CharField()
  class_name       = CharField()
  configuration    = JSONField(default={})
  settings         = JSONField(default={})
  event_listeners  = JSONField(default={})

  @property
  def service_name(self):
      return self.name

  @service_name.setter
  def service_name(self, val):
    name = "-".join(re.sub(r'[^a-zA-Z0-9\-_\s]', '', val).split(' '))
    self.name = name
  

  @property
  def serialize(self):
    return {
      'id':          self.id,
      'name':        self.name,
      'kind':        self.kind,
      'class_name':  self.kind,
      'settings':  self.settings
    }
  
  @property
  def model(self):    
    _model = None
    if self.kind == "printer":
      from .printer import Printer
      _model = Printer.select().where(Printer.service == self).first()
    elif self.kind == "camera":
      from .camera import Camera
      _model = Camera.select().where(Camera.service == self).first()
    return _model

  @property
  def api_prefix(self):
    if self.id:
      return f"/services/{self.kind}/{self.id}/"
    return "/"


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.kind
    )

  class Meta:
    table_name = "services"

