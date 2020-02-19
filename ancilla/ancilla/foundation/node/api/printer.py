'''
 printer.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time

import math
import os
from .api import Api
from ..events.printer import Printer as PrinterEvent
from ...data.models import Print, Printer, Service, PrinterCommand, CameraRecording
from ..response import AncillaError
from ..request import Request

import asyncio
class PrinterApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/print', 'POST', self.print)
    self.service.route('/prints', 'GET', self.prints)
    self.service.route('/commands', 'GET', self.printer_commands)
    self.service.route('/commands', 'DELETE', self.delete_printer_commands)
    self.service.route('/prints/<print_id>/sync_layerkeep', 'POST', self.sync_print_to_layerkeep)
    self.service.route('/prints/<print_id>/unsync_layerkeep', 'POST', self.unsync_print_from_layerkeep)
    self.service.route('/prints/<print_id>/recordings', 'GET', self.get_print_recordings)
    self.service.route('/prints/<print_id>', 'GET', self.get_print)
    self.service.route('/prints/<print_id>', 'DELETE', self.delete_print)
    self.service.route('/prints/<print_id>', 'PATCH', self.update_print)
    self.service.route('/logs/<logname>', 'DELETE', self.delete_logfile)
    self.service.route('/logs/<logname>', 'GET', self.logfile)
    self.service.route('/logs', 'GET', self.logs)
    self.service.route('/', 'PATCH', self.update_service)

  async def update_service(self, request, layerkeep, *args):
    ## Do a select instead of using the service model in order to know what changed 
    ## in the post_save handler in the Node service

    s = Service.get_by_id(self.service.model.id)

    frozen_keys = ['id', 'created_at', 'updated_at', 'service', 'layerkeep_id']
    with Service._meta.database.atomic() as transaction:
      try:
        
        newname = request.params.get("name")
        if newname:
          s.service_name = newname
        model = s.model

        if model:
          modelkeys = model.__data__.keys() - frozen_keys
          for k in modelkeys:
            kval = request.params.get(k)
            if kval:
              model.__setattr__(k, kval)

          if not model.is_valid:
            raise AncillaError(400, {"errors": model.errors})
            # return {"errors": model.errors}
          
          lksync = request.params.get("layerkeep_sync")

          if lksync and lksync != 'false':
            if layerkeep:  
              if model.layerkeep_id:
                response = await layerkeep.update_printer({"data": model.to_json(recurse=False)})
              else:
                response = await layerkeep.create_printer({"data": model.to_json(recurse=False)})
              
              if response.success:
                model.layerkeep_id = response.body.get("data").get("id")
              else:
                raise response
                
          elif model.layerkeep_id:
            model.layerkeep_id = None
          
          model.save()          
          

        if request.params.get('configuration') != None:
          s.configuration = request.params.get('configuration')
        if request.params.get('settings') != None:
          s.settings = request.params.get('settings')
        if request.params.get('event_listeners'):
          s.event_listeners = request.params.get('event_listeners')
        s.save()
        smodel = s.json
        smodel.update(model=model.to_json(recurse=False))
        return {"service_model": smodel}
      except Exception as e:
        # Because this block of code is wrapped with "atomic", a
        # new transaction will begin automatically after the call
        # to rollback().
        transaction.rollback()
        # return {"Error"}
        raise e


  def connect(self, *args):
    return self.service.connect()
  
  async def disconnect(self, *args):
    await self.service.stop()
    # if self.service.connector:
    #     self.service.stop()
    return {"status": "disconnected"}

  async def print(self, request, layerkeep, *args):
    resp = await self.service.start_print(request.params)
    data = resp.body
    prnt = data.get("print")
    if request.params.get('layerkeep_sync'):      
      response = await layerkeep.create_print({"data": {"print": prnt, "params": request.params}})

      if not response.success:
        raise response
      
      prnt.layerkeep_id = response.body.get("data").get("id")
      prnt.save()

    return {"data": prnt}
    

  
  def prints(self, request, *args):
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    # print(f'request search params = {request.params}', flush=True)
    # if request.params.get("q[name]"):
    #   print(f'request search params = {request.params.get("q[name]")}', flush=True)

    q = self.service.printer.prints.order_by(Print.created_at.desc())
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=True) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}

  def get_print(self, request, print_id, *args):
    prnt = Print.get_by_id(print_id)
    return {"data": prnt.json}

  def get_print_recordings(self, request, print_id, *args):
    prnt = Print.get_by_id(print_id)
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    # q = self.service.camera_model.recordings.order_by(CameraRecording.created_at.desc())
    q = prnt.recordings
    # if request.params.get("print_id"):
    #   q = q.where(CameraRecording.print_id == request.params.get("print_id"))
    
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=True) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}

  async def sync_print_to_layerkeep(self, request, layerkeep, print_id, *args):
    prnt = Print.get_by_id(print_id)

    if prnt.layerkeep_id:
      response = await layerkeep.update_print({"data": prnt.json})
      if not response.success:
        raise response
    else:
      response = await layerkeep.create_print({"data": {"print": prnt.json, "params": request.params}})
      if not response.success:
        raise response
      prnt.layerkeep_id = response.body.get("data").get("id")
      prnt.save()

    asset_ids = []
    for r in prnt.recordings:
      if r.layerkeep_id:
        asset_ids.append(r.layerkeep_id)
      else:
        data = {
            "params": {
              "layerkeep_id": prnt.layerkeep_id
            },
            "asset": {
                "name": r.task_name + ".mp4",
                "path": r.video_path
            }
          }
        response = await layerkeep.upload_print_asset({"data": data})
        if response.success:
          resdata = response.body.get("data", {})
          assets = resdata.get("attributes", {}).get("assets", [])
          target = next((item for item in assets if item.get("id") not in asset_ids), None)
          if target:
            asset_ids.append(target.get("id"))
          r.layerkeep_id = target.get("id")
          r.save()
        

    
    return {"data": prnt.json}

  async def unsync_print_from_layerkeep(self, request, print_id, *args):
    prnt = Print.get_by_id(print_id)
    prnt.layerkeep_id = None
    prnt.save()
    for r in prnt.recordings:
      r.layerkeep_id = None
      r.save()
    return {"data": prnt.json}


  async def update_print(self, request, layerkeep, print_id, *args):
    prnt = Print.get_by_id(print_id)
    name = request.params.get("name")
    description = request.params.get("description")
    
    if name:
      prnt.name = name
    if description:
      prnt.description = description

    if prnt.layerkeep_id:
      response = await layerkeep.update_print({"data": prnt.json})
      if not response.success:
        raise response
    
    prnt.save()

    recording_id = request.params.get("recording", {}).get("recording_id")
    if recording_id:
      recording = CameraRecording.select().where(CameraRecording.id == recording_id).first()
      if recording:
        recording.print_id = prnt.id
        recording.save()
    return {"data": prnt.json}

  async def delete_print(self, request, layerkeep, print_id, *args):
    prnt = Print.get_by_id(print_id)
    if prnt.layerkeep_id:
      if request.params.get("delete_remote"):
        resp = await layerkeep.delete_print({"data": {"layerkeep_id": prnt.layerkeep_id}})

    if prnt.delete_instance(recursive=True):
      return {"status": 200}
    else:
      raise AncillaError(400, {"error": f"Could Not Delete Print {prnt.name}"})


  def printer_commands(self, request, *args):
    # prnts = Print.select().order_by(Print.created_at.desc())
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    if request.params.get("print_id"):
      prnt = Print.get_by_id(request.params.get("print_id"))
      q = prnt.commands #.order_by(PrinterCommand.created_at.desc())
    else:
      q = self.service.printer.commands #.order_by(PrinterCommand.created_at.desc())

    if request.params.get("q[command]"):
      q = q.where(PrinterCommand.command % (request.params.get("q[command]")+"*"))
    
    # prnt = Print.get_by_id(print_id)
    q = q.order_by(PrinterCommand.id.desc())
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=False) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}
    # return self.service.start_print(request.params)
  
  def delete_printer_commands(self, request, *args):
    if request.params.get("print_id"):
      q = PrinterCommand.delete().where(PrinterCommand.print_id == request.params.get("print_id"))
      cnt = q.execute()
      return {"success": True, "message": f"Deleted {cnt} commands"}
    # else:
    #   q = self.service.printer.commands.order_by(PrinterCommand.created_at.desc())
    return {"success": True}

    
  def logs(self, request, *args):
      log_dir = self.service.config.get("logging.directory")
      logarr = []
      for f in os.listdir(log_dir):
        fstat = os.stat(f"{log_dir}/{f}")        
        # print(f"Fstat = {fstat}", flush=True)
        logarr.append({"filename": f, "size": fstat.st_size, "mtime": fstat.st_mtime})
      
      return {"data": logarr}

  def logfile(self, request, logname, *args):
      log_dir = self.service.config.get("logging.directory")
      logpath = f"{log_dir}/{logname}"
      if not os.path.exists(logpath):
        raise AncillaError(404, "Log File Does Not Exist")

      if request.params.get('download'):
        request.response.set_header('Content-Type', 'application/force-download')
        request.response.set_header('Content-Disposition', 'attachment; filename=%s' % logname)

      return open(logpath)

  def delete_logfile(self, request, logname, *args):
      log_dir = self.service.config.get("logging.directory")
      logpath = f"{log_dir}/{logname}"
      if not os.path.exists(logpath):
        raise AncillaError(404, "Log File Does Not Exist")

      os.remove(logpath)
      return {"success": True}
        

  # def start_print(self, *args):
  #   try:
  #     res = data.decode('utf-8')
  #     payload = json.loads(res)
  #     # name = payload.get("name") or "PrintTask"
  #     method = payload.get("method")
  #     pt = PrintTask("print", request_id, payload)
  #     self.task_queue.put(pt)
  #     loop = IOLoop().current()
  #     loop.add_callback(partial(self._process_tasks))

  #   except Exception as e:
  #     print(f"Cant Start Print task {str(e)}", flush=True)

  #   return {"queued": "success"}

    

  
# @app.route('/hello/<name>')
# def hello(name):
#   return 'Hello %s' % name

# def state(service, *args):
#   return "State"


