'''
 base.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import datetime

from peewee               import Model, DateTimeField, AutoField
from playhouse.shortcuts  import model_to_dict
from peewee_validates     import ModelValidator
from ..db                 import Database

class BaseModel(Model):
  id = AutoField()

  @property
  def json(self):
    return model_to_dict(self)

  @property
  def is_valid(self):
    self.validator = ModelValidator(self)

    return self.validator.validate()


  @property
  def errors(self):
    return self.validator.errors

  class Meta:
    database = Database.conn
