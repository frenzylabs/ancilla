'''
 node.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/14/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera, ServiceAttachment, CameraRecording, Node
from ..response import AncillaError, AncillaResponse


import re
import math
import os
import json

MB = 1 << 20
BUFF_SIZE = 10 * MB

class NodeApi(Api):

  def setup(self):
    super().setup("/api")
    # self.service.route('/services', 'GET', self.services)
    self.service.route('/api/node', 'GET', self.get_node)
    self.service.route('/api/node', 'PATCH', self.update_node)
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

  def get_node(self, request, *args):
    model  = self.service.model
    return {"node": model.json}

  def update_node(self, request, *args):
    model  = self.service.model
    frozen_keys = ['id', 'name', 'original_name', 'created_at', 'updated_at']

    newname = request.params.get("name")
    if newname:
      model.node_name = newname
    
    modelkeys = model.__data__.keys() - frozen_keys
    for k in modelkeys:
      kval = request.params.get(k)
      if kval:
        model.__setattr__(k, kval)

    if not model.is_valid:
      raise AncillaError(400, {"errors": model.errors})
    
    model.save()
    
    return {"node": model}
    # newname = request.params.get("name")
    # n = Node.select().first()

  def discover_nodes(self, request, *args):
    res  = self.service.discovery.nodes()
    # print(f'Node res = {res}')
    nodes = []
    ips = {}
    for r in res:
      if "ip" in r:
        ips[r["ip"]] = r
    networkservices = self.service.discovery.beacon.listener.myservices    

    # {'addresses': ['192.168.1.129'], 'port': 5000, 'server': 'ancilla.local', 'type': '_ancilla._tcp.local.'}
    try:
      for key, ns in networkservices.items():
        
        ip = ns["addresses"][0]
        if ip:
          nd = {"network_name": key}
          if ip in ips:
            nd.update({**ns, **ips[ip]})
            nodes.append(nd)
            del ips[ip]
          else:
            nd.update(ns)
            nodes.append(nd)
    except Exception as e:
      print(f"Node Exception = {str(e)}", flush=True)

    ## The rest of ips not part of the bonjour services for some reason")
    for n in ips.values():
      nodes.append(n)

    return {"nodes": nodes}



  async def delete_service(self, request, layerkeep, service_id, *args):
    smodel = Service.get_by_id(service_id)
    model = smodel.model
    with Service._meta.database.atomic() as transaction:
      try:
        if model:
          # if request.params.get("layerkeep_sync") and request.params.get("layerkeep_sync") != "false":
          if layerkeep and smodel.kind == "printer" and model.layerkeep_id:
            response = await layerkeep.delete_printer({"data": {"layerkeep_id": model.layerkeep_id}})
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
        model = s.model
        newname = request.params.get("name")
        if newname:   
          s.service_name = newname
          

          if model:
            model.name = newname
            if not model.is_valid:
              raise AncillaError(400, {"errors": model.errors})
            model.save()


        if request.params.get('configuration') != None:
          s.configuration = request.params.get('configuration')
        if request.params.get('settings') != None:
          s.settings = request.params.get('settings')

        s.event_listeners = request.params.get('event_listeners') or s.event_listeners
        s.save()
        smodel = s.json
        if model:
          smodel.update(model=model.to_json(recurse=False))
        return {"service_model": smodel}
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
    if request.params.get("q[status]"):
      q = q.where(CameraRecording.status == request.params.get("q[status]"))
    
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
    # path = rcd.video_path + "/output.mp4"    

    fp = open(rcd.video_path, "rb")
    
    request.response.set_header('Content-Disposition', 'filename=%s' % "output.mp4")
    if request.params.get("download"):
      request.response.set_header('Content-Type', 'application/octet-stream')
      return fp

    request.response.status = 206
    request.response.set_header('Content-Type', 'video/mp4')    
    request.response.set_header('Accept-Ranges', 'bytes')

    return self.stream_video(request, fp)

  def list_printers(self, *args, **kwargs):
    return {'printers': [printer.json for printer in Printer.select()]}

  def list_cameras(self, request, *args, **kwargs):
    return {'cameras': [camera.json for camera in Camera.select()]}

  def create_camera(self, request, *args, **kwargs):
    with Service._meta.database.atomic() as transaction:
      try:
        service = Service(name=request.params.get("name"), kind="camera", class_name="Camera")
        service.service_name = request.params.get("name")

        if not service.is_valid:
          raise AncillaError(400, {"errors": service.errors})

        service.save()

        camera = Camera(**request.params, service=service)
        default_settings = {
          "record": {
            "timelapse": 2,
            "frames_per_second": 10,
          },
          "video": {
            "size": [640, 480],
            "format": "avc1"
          }
        }
        camera.settings = default_settings
        if not camera.is_valid:
          raise AncillaError(400, {"errors": camera.errors})

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
    with Service._meta.database.atomic() as transaction:
      try:
        service = Service(name=request.params.get("name"), kind="printer", class_name="Printer")
        service.service_name = request.params.get("name")

        if not service.is_valid:
          raise AncillaError(400, {"errors": service.errors})
        service.save()
        
        printer = Printer(**request.params, service=service)
        if not printer.is_valid:
          raise AncillaError(400, {"errors": printer.errors})

        if request.params.get("layerkeep_sync") == True:
          if layerkeep:  
            response = await layerkeep.create_printer({"data": request.params})
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
    print(f"INSIDECatch service {service} {service_id}", flush=True)
    print(f"INSIDECatch {args},  {kwargs}", flush=True)
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

    return {"retry": True}

  def catchIt(self, name, *args, **kwargs):
    print("INSIDE CATCH IT")
    return {"catch it": True}

