'''
 file.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 11/23/19
 Copyright 2019 FrenzyLabs, LLC.
'''

import os 

from pathlib  import Path  
from .base    import BaseHandler
from ...env   import Env
from ...data.models import Service
import random
import string

from .node_api import NodeApiHandler

from ...node.response import AncillaResponse

class FileResource(NodeApiHandler):
  
  def prepare(self):
    super().prepare()
    service = Service.select().where(Service.kind == "file").where(Service.name == "local").first()
    if service:
      path = ""
      if self.request.path.startswith("/files/"):
        path = self.request.path[len("/files/"):]
      self.environ["PATH"] = service.api_prefix + path 

  async def get(self, *args):
    try:
      resp = await self.node(self.environ)
      self.set_resp_headers(resp)
      self.set_status(resp.status_code)
      if self.params.get("download"):
        self.download_sliced_file(resp)
      else:
        self.write(resp.body)

    except AncillaResponse as e:
      print(f"ancillagetexception = {e}", flush=True)  
      self.set_resp_headers(e)   
      self.set_status(e.status_code)
      self.write(e.body)
    except Exception as e:
      print(f"getexception = {e}", flush=True)    
      self.set_status(400)
      self.write({"error": str(e)})

    finally:
      self.finish()

  def download_sliced_file(self, resp):
    with open(resp.body.get("file").get("path"), "rb") as f:
      try:
        while True:
          _buffer = f.read(4096)
          if _buffer:
            self.write(_buffer)
          else:
            f.close()
            return
      except Exception as e:
        raise e

