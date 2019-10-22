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

class FileHandler(BaseHandler):
  root_path = "/".join([Env.ancilla, "user_files"])

  def post(self):
    incoming        = self.request.files['file'][0]
    original_name   = incoming['name']
    ext             = os.path.splitext(original_name)[1]
    name            = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    filename        = name + ext
    output          = open("{}/{}".format(self.root_path, filename), 'w')

    output.write(incoming['body'])

    self.finish("file: ", + filename + " has been uploaded")

  def get(self):
    path  = Path(self.root_path)
    items = [item for item in path.glob('**/*')]

    self.write({"user_files": items})
