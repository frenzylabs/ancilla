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
from ...data.models import SliceFile
import random
import string


class FileResource(BaseHandler):
  
  def initialize(self, node, **kwargs):    
    self.node = node
    self.root_path = "/".join([Env.ancilla, self.node.name, "user_files"])
    if not os.path.exists(self.root_path):
      os.makedirs(self.root_path)


  def post(self):
    incoming        = self.request.files['file'][0]    
    name            = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    original_name   = incoming.get('filename') or incoming.get('name') or f"{name}.txt"
    ext             = os.path.splitext(original_name)[1]
    filename        = name + ext
    filepath        = self._path_for_file(filename)
    output          = open(filepath, 'wb')
    
    output.write(incoming['body'])
    sf = SliceFile(name=original_name, generated_name=filename, path=filepath)
    sf.save()

    self.finish({"file": sf.json})

  def get(self):

    self.write(
      {'files': [slice_file.json for slice_file in SliceFile.select()]}
    )
    self.finish()

  def delete(self):
    id          = self.get_argument('file_id', None)
    slice_file  = SliceFile.get_by_id(id)

    os.remove(slice_file.path)
    slice_file.delete()

    self.set_status(200, "")
    self.write()

  def _path_for_file(self, filename):
    return "{}/{}".format(self.root_path, filename)
