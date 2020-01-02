import time

import os, random, string
import asyncio
import math 

from .api import Api
from ..events import FileEvent
from ...data.models import PrintSlice
from ..response import AncillaResponse, AncillaError

class FileApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/<file_id>', 'GET', self.get)
    self.service.route('/<file_id>/unsync', 'PATCH', self.unsync_layerkeep)
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

  def unsync_layerkeep(self, request, layerkeep, file_id, *args):
    print_slice  = PrintSlice.get_by_id(file_id)
    print_slice.layerkeep_id = None
    print_slice.save()
    return {"file": print_slice.json}
    # pass

  async def update(self, request, layerkeep, file_id, *args):
    print_slice  = PrintSlice.get_by_id(file_id)
    name = request.params.get("name")
    description = request.params.get("description")
    if name:
      print_slice.name = name
    if description:
      print_slice.description = description

    if print_slice.layerkeep_id:
      response = await layerkeep.update_sliced_file({"data": print_slice.json})    
      if not response.success:
        raise response

    print_slice.save()
    return {"file": print_slice.json}
    


  async def post(self, request, layerkeep, *args):
    print("INSIDE FiLE POST")
    print(request.params, flush=True)
    # print(request.files, flush=True)
    name = request.params.get("name") or ""
    rootname, ext       = os.path.splitext(name)
    description = request.params.get("description") or ""

    incoming        = request.files['file'][0]    
    generated_name  = rootname + "".join(random.choice(string.ascii_lowercase + string.digits) for x in range(6))    
    
    original_name   = incoming.get('filename') or incoming.get('name') or f"{generated_name}.txt"
    root, ext       = os.path.splitext(original_name)
    if name == "":
      name = original_name
    filename        = generated_name + ext
    filepath        = self._path_for_file(filename)
    output          = open(filepath, 'wb')
    
    output.write(incoming['body'])
    output.close()
    
    print_slice = PrintSlice(name=name, generated_name=filename, path=filepath, description=description)
    lksync = request.params.get("layerkeep_sync")

    if lksync and lksync != 'false':
      response = await layerkeep.upload_sliced_file({"data": {"sliced_file": print_slice.json, "params": request.params}})    
      if not response.success:
        raise response
    
      print_slice.layerkeep_id = response.body.get("data").get("id")

    print_slice.save()
    
    self.service.fire_event(FileEvent.created, print_slice.json)
    return {"file": print_slice.json}
    # self.finish({"file": sf.json})

  def list_files(self, request, *args):
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    q = PrintSlice.select().order_by(PrintSlice.created_at.desc())
    
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=True) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}



  def get(self, request, file_id, *args):
    print_slice  = PrintSlice.get_by_id(file_id)
    
    if request.params.get('download'):
      # request.response.set_header()
      request.response.set_header('Content-Type', 'application/force-download')
      request.response.set_header('Content-Disposition', 'attachment; filename=%s' % print_slice.name)
    return {"file": print_slice.json}

  async def delete(self, request, layerkeep, file_id, *args):
    print_slice  = PrintSlice.get_by_id(file_id)
    if print_slice.layerkeep_id:
      resp = await layerkeep.delete_sliced_file({"data": {"layerkeep_id": print_slice.layerkeep_id}})

    if self.service.delete_file(print_slice):
      return {"status": 200}
    else:
      raise AncillaError(400, {"error": f"Could Not Delete File {print_slice.name}"})


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
    layerkeep_id = request.params.get("attributes").get("id")
    localsf = PrintSlice.select().where(PrintSlice.layerkeep_id == layerkeep_id).first()
    if localsf:
      return {"file": localsf.json}

    name = request.params.get("attributes").get("name")
    description = request.params.get("attributes").get("description") or ""
    
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
    sf = PrintSlice(name=name, generated_name=filename, path=filepath, layerkeep_id=request.params.get("id"), description=description, source="layerkeep")
    sf.save()
    self.service.fire_event(FileEvent.created, sf.json)
    return {"file": sf.json}

  async def sync_to_layerkeep(self, request, layerkeep, file_id, *args):
    print(f"sync layerkeep {request.params}", flush=True)
    print_slice  = PrintSlice.get_by_id(file_id)
    if print_slice.layerkeep_id:
      return {"data": print_slice.json}
    
    response = await layerkeep.upload_sliced_file({"data": {"sliced_file": print_slice.json, "params": request.params}})    

    if not response.success:
      raise response
    
    print_slice.layerkeep_id = response.body.get("data").get("id")
    print_slice.save()
    return {"file": print_slice.json}
