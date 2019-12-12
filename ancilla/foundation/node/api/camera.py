import time
from .api import Api
from ..events.camera import Camera as CameraEvent
from ...data.models import Camera, Service
from ..response import AncillaError

import asyncio

class CameraApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/hello', 'GET', self.hello)
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/', ['PATCH', 'PUT'], self.update_service)


  async def update_service(self, request, *args):
    s = self.service.model
    frozen_keys = ['id', 'created_at', 'updated_at', 'service']
    with Service._meta.database.atomic() as transaction:
      try:
        
        newname = request.params.get("name")
        if newname:
          s.name = newname
        model = s.model

        if model:
          modelkeys = model.__data__.keys() - frozen_keys
          for k in modelkeys:
            kval = request.params.get(k)
            if kval:
              model.__setattr__(k, kval)

          if not model.is_valid:
            raise AncillaError(400, {"errors": model.errors})

          model.save()

        if request.params.get('configuration') != None:
          s.configuration = request.params.get('configuration')
        if request.params.get('settings') != None:
          s.settings = request.params.get('settings')
        if request.params.get('event_listeners'):
          s.event_listeners = request.params.get('event_listeners')
        s.save()
        return {"service_model": s.json}
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        # return {"Error"}
        raise e


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

