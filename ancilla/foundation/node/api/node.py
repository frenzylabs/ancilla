import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera, ServiceAttachment

import asyncio

from ..response import AncillaError, AncillaResponse

class NodeApi(Api):

  def setup(self):
    super().setup()
    # self.service.route('/services', 'GET', self.services)
    self.service.route('/services', 'GET', self.services)
    # self.service.route('/services/<service_id>/restart', 'GET', self.restart_service)
    self.service.route('/attachments/<attachment_id>', 'PATCH', self.update_attachment)
    self.service.route('/services/<service_id>', 'PATCH', self.update_service_model)
    self.service.route('/services/<service_id>', 'DELETE', self.delete_service)
    self.service.route('/services/<service_id>/stop', 'GET', self.stop_service)
    self.service.route('/services/testing/<name>', 'GET', self.testname)
    self.service.route('/test', 'GET', self.test)
    self.service.route('/smodel/<model_id>', 'GET', self.service_model)
    self.service.route('/smodel/<service_id>', ['POST', 'PATCH'], self.update_service_model)
    self.service.route('/services/test', 'GET', self.test)
    self.service.route('/services/camera', 'GET', self.list_cameras)
    self.service.route('/services/camera', 'POST', self.create_camera)
    self.service.route('/services/printer', 'POST', self.create_printer)
    self.service.route('/services/printer', 'GET', self.list_printers)
    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
    # self.service.route('/services/<name><other:re:.*>', 'GET', self.catchIt)

  async def delete_service(self, request, layerkeep, service_id, *args):
    print(f"SERVICE args = {service_id}", flush=True)
    smodel = Service.get_by_id(service_id)
    model = smodel.model
    with Service._meta.database.atomic() as transaction:
      try:
        if model:          
          # if request.params.get("layerkeep_sync") and request.params.get("layerkeep_sync") != "false":
          if layerkeep and smodel.kind == "printer" and model.layerkeep_id:
            response = await layerkeep.delete_printer({"data": {"layerkeep_id": model.layerkeep_id}})
            print(f"LK response = {response.status}  {response.body}", flush=True)
            if not response.success:
              raise response
          model.delete_instance(recursive=True)
              
        smodel.delete_instance(recursive=True)
        self.service.delete_service(smodel)
      except Exception as e:
        print(f"DELETE SERvice excption= {str(e)}", flush=True)
        transaction.rollback()    
        raise e
        # return {"error": "Could Not Delete Service"}
    
    return {"success": True}

  def stop_service(self, request, service_id, *args):
    s = Service.get_by_id(service_id)
    self.service.stop_service(s)
    return {"success": True}

  def services(self, request, *args):
    allservices = []
    q = Service.select()
    if request.params.get("kind"):
      q = q.where(Service.kind == request.params.get("kind"))

    for service in q:
      js = service.json
      model = service.model
      if model:
        js.update(model=model.to_json(recurse=False))
      allservices.append(js)
    
    return {'services': allservices}

    # return {'services': [service.json for service in Service.select()]}

  def actions(self, *args):
    return {"actions": self.service.list_actions()}

  def service_model(self, request, model_id, *args):  
    s = Service.get_by_id(model_id)
    return {"service_model": s.json}

  def update_service_model(self, request, layerkeep, service_id, *args):
    s = Service.get_by_id(service_id)
    
    with Service._meta.database.atomic() as transaction:
      try:
        
        newname = request.params.get("name")
        if newname:
          s.name = newname
          model = s.model
          # if s.kind == "printer":
          #   obj = Printer.select().where(Printer.service == s ).first()
          # elif s.kind == "camera":
          #   obj = Camera.select().where(Camera.service == s ).first()

          if model:
            model.name = newname
            if not model.is_valid:
              raise AncillaError(400, {"errors": model.errors})
              # return {"errors": model.errors}
            model.save()


        print(f"Serv Config= {request.params.get('configuration')}", flush=True)
        if request.params.get('configuration') != None:
          print('Has config', flush=True)
          s.configuration = request.params.get('configuration')
        if request.params.get('settings') != None:
          print('Has settings', flush=True)
          s.settings = request.params.get('settings')

        # s.settings = request.params.get('settings') or s.settings
        # s.configuration = request.params.get('configuration') or s.configuration
        s.event_listeners = request.params.get('event_listeners') or s.event_listeners
        s.save()
        return {"service_model": s.json}
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        # return {"Error"}
        raise e

  # def register_event_listeners(self, *args):

  def delete_service_model(self, request, model_id, *args):    
    s = Service.get_by_id(model_id)
    self.service.remove_service()
    list_1 = [item for item in list_1 if item[2] >= 5 or item[3] >= 0.3]
    

  def testname(self, request, name, *args, **kwargs):
    print(f"INSIDE Test name {name}", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    return {"success": "tada"}

  def list_printers(self, *args, **kwargs):
    print("INSIDE LIST Printers", flush=True)
    print(f"args = {args}", flush=True)
    return {'printers': [printer.json for printer in Printer.select()]}

  def list_cameras(self, request, *args, **kwargs):
    print("INSIDE LIST CAMERAs", flush=True)
    print(f"args = {args}", flush=True)
    print(f"kwargs = {kwargs}", flush=True)
    print(f"REQUEST PARAMs = {request.params}", flush=True)
    return {'cameras': [camera.json for camera in Camera.select()]}

  def create_camera(self, request, *args, **kwargs):
    print("INSIDE CREATE CAMERAs", flush=True)

    with Service._meta.database.atomic() as transaction:
      try:
        service = Service(name=request.params.get("name"), kind="camera", class_name="Camera")

        if not service.is_valid:
          raise AncillaError(400, {"errors": service.errors})
          # return {"status": 400, "errors": service.errors}
        service.save()

        camera = Camera(**request.params, service=service)
        if not camera.is_valid:
          raise AncillaError(400, {"errors": camera.errors})
          # return {"status": 400, "errors": camera.errors}

        camera.save()
        camera_service = service.json
        camera_service.update(model=camera.json)
        return {"camera": camera_service} 
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        raise e

  async def create_printer(self, request, layerkeep, *args, **kwargs):
    print("INSIDE CREATE Printer", flush=True)


    with Service._meta.database.atomic() as transaction:
      try:
        service = Service(name=request.params.get("name"), kind="printer", class_name="Printer")

        if not service.is_valid:
          raise AncillaError(400, {"errors": service.errors})
          # return {"status": 400, "errors": service.errors}
        service.save()
        
        printer = Printer(**request.params, service=service)
        if not printer.is_valid:
          raise AncillaError(400, {"errors": printer.errors})
          # return {"status": 400, "errors": printer.errors}

        # print(f"Layerkeep = {layerkeep}", flush=True)
        if request.params.get("layerkeep_sync") == True:
          if layerkeep:  
            response = await layerkeep.create_printer({"data": request.params})
            print(f"LK response = {response.status}  {response.body}", flush=True)
            if response.success:
              printer.layerkeep_id = response.body.get("data").get("id")
            else:
              raise response

        printer.save()
        printerservice = service.json
        printerservice.update(model=printer.json)
        return {"printer": printerservice} 
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        raise e


  async def update_attachment(self, request, attachment_id, *args):
    sa = ServiceAttachment.get_by_id(attachment_id)
    if request.params.get("settings"):
      sa.settings = request.params.get("settings")
      sa.save()
    return {"data": sa.json}

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

