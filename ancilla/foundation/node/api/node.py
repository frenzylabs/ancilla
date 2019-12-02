import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera

import asyncio

class NodeApi(Api):

  def setup(self):
    self.service.route('/services', 'GET', self.services)
    self.service.route('/services/testing/<name>', 'GET', self.testname)
    self.service.route('/test', 'GET', self.test)
    self.service.route('/smodel/<model_id>', 'GET', self.service_model)
    self.service.route('/smodel/<model_id>', ['POST', 'PATCH'], self.update_service_model)
    self.service.route('/services/test', 'GET', self.test)
    self.service.route('/services/camera', 'GET', self.listCameras)
    self.service.route('/services/camera', 'POST', self.createCamera)
    self.service.route('/services/printer', 'POST', self.createPrinter)
    self.service.route('/services/printer', 'GET', self.listPrinters)
    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
    # self.service.route('/services/<name><other:re:.*>', 'GET', self.catchIt)

  # _SERVICE_MODELS_ = ['printer', 'camera']
  def services(self, *args):
    allservices = []
    for service in Service.select():
      js = service.json
      model = service.model
      if model:
        js.update(model=model.to_json(recurse=False))
      allservices.append(js)
    
    return {'services': allservices}

    # return {'services': [service.json for service in Service.select()]}

  def actions(self, *args):
    return {"actions": self.service.actions()}

  def service_model(self, request, model_id, *args):  
    s = Service.get_by_id(model_id)
    return {"service_model": s.json}

  def update_service_model(self, request, model_id, *args):
    s = Service.get_by_id(model_id)
    
    newname = request.params.get("name")
    if newname:
      s.name = newname
      obj = None
      if s.kind == "printer":
        obj = Printer.select().where(Printer.service == s ).first()
      elif s.kind == "camera":
        obj = Camera.select().where(Camera.service == s ).first()

      if obj:
        obj.name = newname
        if not obj.is_valid:
          return {"errors": obj.errors}

          
    s.settings = request.params.get('settings') or s.settings
    s.configuration = request.params.get('configuration') or s.configuration
    s.save()
    return {"service_model": s.json}
  # def register_event_listeners(self, *args):

    

  def testname(self, request, name, *args, **kwargs):
    print(f"INSIDE Test name {name}", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    return {"success": "tada"}

  def listPrinters(self, *args, **kwargs):
    print("INSIDE LIST Printers", flush=True)
    print(f"args = {args}", flush=True)
    return {'printers': [printer.json for printer in Printer.select()]}

  def listCameras(self, request, *args, **kwargs):
    print("INSIDE LIST CAMERAs", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    print(f"REQUEST PARAMs = {request.params}", flush=True)
    return {'cameras': [camera.json for camera in Camera.select()]}

  def createCamera(self, request, *args, **kwargs):
    print("INSIDE CREATE CAMERAs", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    print(f"name = {request}", flush=True)
    print(f"name = {request.params}", flush=True)

    service = Service(name=request.params.get("name"), kind="camera", class_name="Camera")

    if not service.is_valid:
      return {"status": 400, "errors": service.errors}
    service.save()

    camera = Camera(**request.params, service=service)
    if not camera.is_valid:
      return {"status": 400, "errors": camera.errors}

    camera.save()
    return {"camera": camera.json}

  def createPrinter(self, request, *args, **kwargs):
    print("INSIDE CREATE Printer", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    print(f"name = {request}", flush=True)
    print(f"name = {request.params}", flush=True)

    service = Service(name=request.params.get("name"), kind="printer", class_name="Printer")

    if not service.is_valid:
      return {"status": 400, "errors": service.errors}
    service.save()
    
    printer = Printer(**request.params, service=service)
    if not printer.is_valid:
      return {"status": 400, "errors": printer.errors}

    printer.save()
    return {"printer": printer.json} 



  async def test(self, request, *args, **kwargs):
    print("INSIDE TEST", flush=True)      
    print(self)
    print(f"REQUEST ENV = {request.environ}", flush=True)
    print(args, flush=True)
    print(self.routes, flush=True)
    await asyncio.sleep(2)
    print("Test AFter first sleep", flush=True)
    print(f"REQUEST ENV = {request.environ}", flush=True)
    await asyncio.sleep(5)
    print("TestAFter 2 sleep", flush=True)
    print(f"REQUEST ENV = {request.environ}", flush=True)
    return "woohoo"

  def catchUnmountedServices(self, request, service, service_id, *args, **kwargs):
    print("INSIDE CATCH service")
    print(f"INSIDECatch {service} {service_id}", flush=True)
    print(f"INSIDECatch {args},  {kwargs}", flush=True)
    print(f"Request = {request}", flush=True)
    print(f"Request = {request.params}", flush=True)
    
    try:
      s = Service.get_by_id(service_id)
      status, module = self.service.mount_service(s)
      if status == "created":
        return request.app._handle(request.environ)
      else:
        return {"status": "error", "error": "No Route"}
    except Exception as e:
      print(f"Could not mount service {str(e)}")
      return {"error": str(e)}

    
    # self.__handle
    return {"retry": True}

  def catchIt(self, name, *args, **kwargs):
    print("INSIDE CATCH IT")
    print(f"INSIDECatch {name}", flush=True)
    print(f"INSIDECatch {args},  {kwargs}", flush=True)
    return {"catch it": True}

