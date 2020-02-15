'''
 node.py
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


class Node(BaseModel):
  name             = CharField()
  original_name    = CharField()
  uuid             = CharField()
  description      = CharField(null=True)
  configuration    = JSONField(default=dict)
  settings         = JSONField(default=dict)
  event_listeners  = JSONField(default=dict)

  @property
  def node_name(self):
      return self.name

  @node_name.setter
  def node_name(self, val):
    name = "-".join(re.sub(r'[^a-zA-Z0-9\-_\s]', '', val).split(' '))
    self.name = name
    self.original_name = val
  

  @property
  def serialize(self):
    return {
      'id':             self.id,
      'name':           self.name,
      'original_name':  self.original_name,
      'uuid':           self.uuid,
      'settings':       self.settings
    }
  


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.name, 
      self.uuid
    )

  class Meta:
    table_name = "nodes"

