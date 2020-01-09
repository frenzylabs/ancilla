import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera, ServiceAttachment, CameraRecording
from ..response import AncillaError, AncillaResponse


import asyncio
import re
import math
import os
# import bluetooth

MB = 1 << 20
BUFF_SIZE = 10 * MB

class NodeApi(Api):

  def setup(self):
    super().setup("/api")
    # self.service.route('/services', 'GET', self.services)
    self.service.route('/api/nodes', 'GET', self.discover_nodes)
    self.service.route('/api/services', 'GET', self.services)
    self.service.route('/api/recordings', 'GET', self.recordings)
    self.service.route('/api/recordings/<recording_id>', 'GET', self.get_recording)
    self.service.route('/api/recordings/<recording_id>', 'DELETE', self.delete_recording)
    self.service.route('/api/recordings/<recording_id>/video', 'GET', self.get_video)
    
    # self.service.route('/services/<service_id>/restart', 'GET', self.restart_service)
    self.service.route('/api/attachments/<attachment_id>', 'PATCH', self.update_attachment)
    self.service.route('/api/services/<service_id>', 'PATCH', self.update_service_model)
    self.service.route('/api/services/<service_id>', 'DELETE', self.delete_service)
    self.service.route('/api/services/<service_id>/stop', 'GET', self.stop_service)    
    self.service.route('/api/services/camera', 'GET', self.list_cameras)
    self.service.route('/api/services/camera', 'POST', self.create_camera)
    self.service.route('/api/services/printer', 'POST', self.create_printer)
    self.service.route('/api/services/printer', 'GET', self.list_printers)
    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
    # self.service.route('/services/<name><other:re:.*>', 'GET', self.catchIt)

  def discover_nodes(self, request, *args):
    self.service.discovery.send([b'peers', b'tada'])
    return {"success": "sent"}
  #   nearby_devices = bluetooth.discover_devices(lookup_names=True)
  #   print("Found {} devices.".format(len(nearby_devices)))

  #   return {"devices": [{addr: name} for addr, name in nearby_devices]}
      # print("  {} - {}".format(addr, name))
    

  async def delete_service(self, request, layerkeep, service_id, *args):
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
          s.service_name = newname
          model = s.model

          if model:
            model.name = newname
            if not model.is_valid:
              raise AncillaError(400, {"errors": model.errors})
            model.save()


        # print(f"Serv Config= {request.params.get('configuration')}", flush=True)
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
    

  def recordings(self, request, *args, **kwargs):
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    q = CameraRecording.select().order_by(CameraRecording.created_at.desc())
    if request.params.get("q[print_id]"):
      q = q.where(CameraRecording.print_id == request.params.get("q[print_id]"))
    if request.params.get("q[camera_id]"):
      q = q.where(CameraRecording.camera_id == request.params.get("q[camera_id]"))
    
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=True) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}

  def get_recording(self, request, recording_id, *args):
    rcd = CameraRecording.get_by_id(recording_id)
    return {"data": rcd.json}
  
  def delete_recording(self, request, recording_id, *args):
    rcd = CameraRecording.get_by_id(recording_id)
    if self.service.delete_recording(rcd):
      return {"success": "Deleted"}
    raise AncillaError(400, {"errors": "Coud Not Delete Recording"})

  def get_video(self, request, recording_id, *args):
    rcd = CameraRecording.get_by_id(recording_id)
    path = rcd.video_path + "/output.mp4"    
    fp = open(path, "rb")
    
    request.response.set_header('Content-Disposition', 'filename=%s' % "output.mp4")
    if request.params.get("download"):
      request.response.set_header('Content-Type', 'application/octet-stream')
      return fp

    request.response.status = 206
    request.response.set_header('Content-Type', 'video/mp4')    
    request.response.set_header('Accept-Ranges', 'bytes')

    return self.stream_video(request, fp)

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

  def stream_video(self, request, fp):    
    start, end = self.get_range(request)

    requestedrange =  request.headers.get('Range')
    # if requestedrange == None:
    #   print("NO REQUESTED RANGE",flush=True)
    # else:
    file_size = os.path.getsize(fp.name)
    if end is None:
        end = start + BUFF_SIZE - 1
    end = min(end, file_size - 1)
    end = min(end, start + BUFF_SIZE - 1)
    length = end - start + 1
    # resp.body.buffer_size = length

    request.response.set_header(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    fp.seek(start)
    bytes = fp.read(length)
    return bytes

  def get_range(self, request):
    range = request.headers.get('Range')
    m = None
    if range:
      m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None

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

