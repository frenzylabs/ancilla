'''
 datastore.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/22/19
 Copyright 2019 Wess Cope
'''

import json

from .base import BaseHandler

class DocumentResource(BaseHandler):
  def initialize(self, document_store):
    self.document_store = document_store

  def get(self, *args, **kwargs):
    key = self.params.get('key', None)

    if not key:
      self.write(dict(items=self.document_store.items()))
      return

    if self.document_store.keys().includes(key):
      self.write(404, {key : 'not found'})
      return

    self.write({key: self.document_store.get(key)})

  def post(self, *args, **kwargs):
    key = self.params.get('key', None)
    val = self.params.get('value', None)

    self.document_store.update(**{key: val})

    self.write({key: self.document_store.get(key)})

  def delete(self, key, *args, **kwargs):
    result = self.document_store.pop(key)

    self.write(dict(deleted=key))
