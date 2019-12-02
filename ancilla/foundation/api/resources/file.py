'''
 file.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/22/19
 Copyright 2019 Wess Cope
'''

import os 

from pathlib  import Path  
from .base    import BaseHandler
from ...env   import Env
from ...data.models import Service
import random
import string

from .node_api import NodeApiHandler

class FileResource(NodeApiHandler):
  
  def prepare(self):
    super().prepare()
    q = Service.select().where(Service.kind == "file" and Service.name == "local")
    if (len(q) > 0):
      service = q.get()
      self.environ["PATH"] = service.api_prefix

