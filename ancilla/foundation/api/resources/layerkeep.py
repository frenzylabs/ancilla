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

class LayerkeepResource(NodeApiHandler):
  
  def prepare(self):
    super().prepare()
    service = Service.select().where(Service.kind == "layerkeep").first()
    if service:    
      path = ""
      if self.request.path.startswith("/api/layerkeep/"):
        path = self.request.path[len("/api/layerkeep/"):]
      self.environ["PATH"] = service.api_prefix + path 

  # async def delete(self, *args):    
  #   print("Start delete request", self.request)
  #   try:

  #     # resp = await self.test()
  #     # file_id = self.get_argument('file_id', None)
  #     # print(f"Fileid = {file_id}", flush=True)
  #     # print(f"del env= {self.environ}", flush=True)
  #     resp = await self.node._handle(self.environ)
  #     # resp = await self.node.make_request(self.request)
  #     # print(f"DELETE REPONSE= {resp}", flush=True)
  #     self.write(resp)
  #   except Exception as e:
  #     print(f"deleteexception = {e}", flush=True)          
  #   finally:
  #     self.finish()

