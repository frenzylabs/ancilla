'''
 base.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import time
from peewee               import Model, DateTimeField, AutoField, BigIntegerField
from playhouse.shortcuts  import model_to_dict
from peewee_validates     import ModelValidator
from ..db                 import Database

class BaseModel(Model):
  id = AutoField()
  created_at = BigIntegerField() 
  updated_at = BigIntegerField() 

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

  def save(self, *args, **kwargs):
    t = time.time()
    if not self.created_at:
      self.created_at = t
    self.updated_at = t
     
    super().save(*args, **kwargs)  
    

  class Meta:
    database = Database.conn
