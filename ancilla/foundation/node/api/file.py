import time

import os, random, string
import asyncio

from .api import Api
from ..events import FileEvent
from ...data.models import SliceFile

class FileApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/<file_id>', 'GET', self.get)
    self.service.route('/', 'GET', self.list_files)
    self.service.route('/', 'POST', self.post)
    self.service.route('/<file_id>', 'DELETE', self.delete)
    # self.service.route('/', 'DELETE', self.delete)


  # def initialize(self, node, **kwargs):    
  #   self.node = node
  #   self.root_path = "/".join([Env.ancilla, self.node.name, "user_files"])
  #   if not os.path.exists(self.root_path):
  #     os.makedirs(self.root_path)


  def post(self, request, *args):
    # print("INSIDE FiLE POST")
    # print(request.files, flush=True)
    incoming        = request.files['file'][0]    
    name            = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    original_name   = incoming.get('filename') or incoming.get('name') or f"{name}.txt"
    ext             = os.path.splitext(original_name)[1]
    filename        = name + ext
    filepath        = self._path_for_file(filename)
    output          = open(filepath, 'wb')
    
    output.write(incoming['body'])
    sf = SliceFile(name=original_name, generated_name=filename, path=filepath)
    sf.save()
    self.service.fire_event(FileEvent.created, sf.json)
    return {"file": sf.json}
    # self.finish({"file": sf.json})

  def list_files(self, request, *args):
    return {'files': [slice_file.json for slice_file in SliceFile.select()]}


  def get(self, request, file_id, *args):
    # id          = self.get_argument('file_id', None)
    # file
    slice_file  = SliceFile.get_by_id(file_id)
    return {"file": slice_file.json}

  def delete(self, request, file_id, *args):
    print("INSIDE DELETE FILE", flush=True)
    slice_file  = SliceFile.get_by_id(file_id)
    if self.service.delete_file({"data": slice_file.json}):
      return {"status": 200}
    else:
      return {"status": 400, "error": f"Could Not Delete File {slice_file.name}"}
    # os.remove(slice_file.path)
    # slice_file.delete()
    


    # return {"status": 200}
    # self.set_status(200, "")
    # self.write()

  def _path_for_file(self, filename):
    return "{}/{}".format(self.service.root_path, filename)


  async def hello(self, request, *args, **kwargs):
    print("INSIDE HELLO")
    print(self)
    await asyncio.sleep(2)
    print("Hello AFter first sleep", flush=True)
    await asyncio.sleep(5)
    print("Hello AFter 2 sleep", flush=True)
    return "hello"

  def connect(self, *args):
    return self.service.connect()
  
  def disconnect(self, *args):
    if self.service.connector:
        self.service.stop()
    return {"status": "disconnected"}