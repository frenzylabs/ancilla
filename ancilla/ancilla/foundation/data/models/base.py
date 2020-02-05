'''
 base.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import time
from peewee               import DateTimeField, AutoField, BigIntegerField
from playhouse.shortcuts  import model_to_dict
from peewee_validates     import ModelValidator
from ..db                 import Database

from playhouse.signals import Model

class BaseModel(Model):
  id = AutoField()
  created_at = BigIntegerField() 
  updated_at = BigIntegerField() 

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    t = time.time()
    if not self.created_at:
      self.created_at = t
      self.updated_at = t
        # if kwargs.pop('__no_default__', None):
        #     self.__data__ = {}
        # else:
        #     self.__data__ = self._meta.get_default_dict()
        # self._dirty = set(self.__data__)
        # self.__rel__ = {}

        # for k in kwargs:
        #     setattr(self, k, kwargs[k])

  @property
  def json(self):
    return model_to_dict(self)

  def to_json(self, **kwargs):
    default = {"recurse": False}
    default.update(kwargs)
    return model_to_dict(self, **default)
  # model_to_dict(model, recurse=True, backrefs=False, only=None,
  #                 exclude=None, seen=None, extra_attrs=None,
  #                 fields_from_query=None, max_depth=None, manytomany=False):

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
