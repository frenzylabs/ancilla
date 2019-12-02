import time
from .api import Api
from ..events.camera import Camera as CameraEvent
from ...data.models import Camera

import asyncio

class CameraApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/hello', 'GET', self.hello)
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/', ['PATCH', 'PUT'], self.update_model)



  def update_model(self, request, *args, **kwargs):
    print("UPDATE MODEL")
    print(self.service)
    print(f"model = {self.service.model}", flush=True)
    print(f"request.params = {request.params}")
    model = self.service.model
    # if request.params.get("configuration"):
    c = request.params.get("configuration") or {}
    model.configuration.update(c)
    if request.params.get("name"):
      model.name = request.params["name"]
    model.save()
    self.service.config.update(c)
    
    # Service.update(**request.params).where(Entry.id == entry.id).execute()
    # self.service.model(**request.params)
    print(f"request.environ = {request.environ}")
    # self.service.model.save()
    return {"camera": model.json}


  async def hello(self, request, *args, **kwargs):
    print("INSIDE HELLO")
    print(self)
    print(f"HELLO_REQUEST ENV1 = {request.environ}", flush=True)
    print(f"HELLO_REQUEST ENV1 URLARGS = {request.url_args}", flush=True)
    
    await asyncio.sleep(2)
    print("Hello AFter first sleep", flush=True)
    print(f"HELLO_REQUEST ENV2 = {request.environ}", flush=True)
    await asyncio.sleep(5)    
    print("Hello AFter 2 sleep", flush=True)
    print(f"HELLO_REQUEST ENV3 = {request.environ}", flush=True)
    return "hello"

  def connect(self, *args):
    return self.service.connect()
  
  def disconnect(self, *args):
    if self.service.connector:
        self.service.stop()
    return {"status": "disconnected"}

