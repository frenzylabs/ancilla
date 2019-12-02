'''
 service.py
 models

 Created by Kevin Musselman (kmussel@gmail.com) on 11/01/19
 Copyright 2019 Frenzylabs, LLC
'''

from .base import BaseModel
# from .printer import Printer

from peewee import (
  CharField,
  TextField,
  IntegerField
)

from playhouse.sqlite_ext import JSONField


class Service(BaseModel):
  name          = CharField()
  kind          = CharField()
  class_name    = CharField()
  configuration = JSONField(default={})
  settings      = JSONField(default={})
  event_listeners = JSONField(default={})

  @property
  def serialize(self):
    return {
      'id':          self.id,
      'name':        self.name,
      'kind':        self.kind,
      'class_name':  self.kind,
      'settings':  self.settings
    }
  
  # @property
  # def model(self):
  #   if self.kind == "printer":
  #     Printer

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

