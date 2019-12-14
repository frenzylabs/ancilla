import time

import os, random, string
import asyncio

from .api import Api
from ..events import FileEvent
from ...data.models import SliceFile
from ..response import AncillaResponse, AncillaError

class FileApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/<file_id>', 'GET', self.get)
    self.service.route('/<file_id>', 'PATCH', self.update)
    self.service.route('/<file_id>/sync_layerkeep', 'POST', self.sync_to_layerkeep)
    self.service.route('/sync_layerkeep', 'POST', self.sync_from_layerkeep)
    self.service.route('/', 'GET', self.list_files)
    self.service.route('/', 'POST', self.post)
    self.service.route('/<file_id>', 'DELETE', self.delete)
    # self.service.route('/', 'DELETE', self.delete)


  # def initialize(self, node, **kwargs):    
  #   self.node = node
  #   self.root_path = "/".join([Env.ancilla, self.node.name, "user_files"])
  #   if not os.path.exists(self.root_path):
  #     os.makedirs(self.root_path)

  def update(self, request, layerkeep, *args):
    pass


  def post(self, request, layerkeep, *args):
    print("INSIDE FiLE POST")
    print(request.params, flush=True)
    # print(request.files, flush=True)
    incoming        = request.files['file'][0]    
    name            = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    original_name   = incoming.get('filename') or incoming.get('name') or f"{name}.txt"
    ext             = os.path.splitext(original_name)[1]
    filename        = name + ext
    filepath        = self._path_for_file(filename)
    output          = open(filepath, 'wb')
    
    output.write(incoming['body'])
    output.close()
    sf = SliceFile(name=original_name, generated_name=filename, path=filepath)
    sf.save()
    self.service.fire_event(FileEvent.created, sf.json)
    return {"file": sf.json}
    # self.finish({"file": sf.json})

  def list_files(self, request, *args):
    return {'files': [slice_file.json for slice_file in SliceFile.select()]}


  def get(self, request, file_id, *args):
    slice_file  = SliceFile.get_by_id(file_id)
    return {"file": slice_file.json}

  async def delete(self, request, layerkeep, file_id, *args):
    print("INSIDE DELETE FILE", flush=True)
    slice_file  = SliceFile.get_by_id(file_id)
    if slice_file.layerkeep_id:
      resp = await layerkeep.delete_sliced_file({"data": {"layerkeep_id": slice_file.layerkeep_id}})

    if self.service.delete_file(slice_file):
      return {"status": 200}
    else:
      raise AncillaError(400, {"error": f"Could Not Delete File {slice_file.name}"})


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

  
  async def sync_from_layerkeep(self, request, layerkeep, *args):
    print(f"sync layerkeep {request.params}", flush=True)
    name = request.params.get("attributes").get("name")
    response = await layerkeep.download_sliced_file({"data": request.params})
    if not response.success:
      raise response

    filename            = "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    ext             = os.path.splitext(name)[1]
    filename = filename + ext
    filepath        = self._path_for_file(filename)
    output          = open(filepath, 'wb')
    
    output.write(response.body)
    output.close()
    sf = SliceFile(name=name, generated_name=filename, path=filepath, layerkeep_id=request.params.get("id"), source="layerkeep")
    sf.save()
    self.service.fire_event(FileEvent.created, sf.json)
    return {"file": sf.json}

  async def sync_to_layerkeep(self, request, layerkeep, file_id, *args):
    print(f"sync layerkeep {request.params}", flush=True)
    sliced_file  = SliceFile.get_by_id(file_id)
    if sliced_file.layerkeep_id:
      return {"data": sliced_file.json}
    
    response = await layerkeep.upload_sliced_file({"data": {"sliced_file": sliced_file.json, "params": request.params}})    

    if not response.success:
      raise response
    
    sliced_file.layerkeep_id = response.body.get("data").get("id")
    sliced_file.save()
    return {"data": sliced_file.json}
