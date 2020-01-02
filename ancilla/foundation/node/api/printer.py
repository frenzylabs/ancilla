import time

import math
from .api import Api
from ..events.printer import Printer as PrinterEvent
from ...data.models import Print, Printer, Service, PrinterCommand, CameraRecording
from ..response import AncillaError

import asyncio
class PrinterApi(Api):
  # def __init__(self, service):
  #   super().__init__(service)
  #   self.setup_api()
    

  def setup(self):
    super().setup()
    self.service.route('/hello', 'GET', self.hello)
    self.service.route('/connection', 'POST', self.connect)
    self.service.route('/connection', 'DELETE', self.disconnect)
    self.service.route('/print', 'POST', self.print)
    self.service.route('/prints', 'GET', self.prints)
    self.service.route('/commands', 'GET', self.printer_commands)
    self.service.route('/prints/<print_id>/sync_layerkeep', 'POST', self.sync_print_to_layerkeep)
    self.service.route('/prints/<print_id>/unsync_layerkeep', 'POST', self.unsync_print_from_layerkeep)
    self.service.route('/prints/<print_id>/recordings', 'GET', self.get_print_recordings)
    self.service.route('/prints/<print_id>', 'GET', self.get_print)
    self.service.route('/prints/<print_id>', 'DELETE', self.delete_print)
    self.service.route('/', 'PATCH', self.update_service)

  async def update_service(self, request, layerkeep, *args):
    s = self.service.model
    frozen_keys = ['id', 'created_at', 'updated_at', 'service', 'layerkeep_id']
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

  async def hello(self, request, layerkeep, *args, **kwargs):
    print("INSIDE HELLO")
    print(layerkeep)
    await asyncio.sleep(2)
    print("Hello AFter first sleep", flush=True)
    # await asyncio.sleep(2)
    # print("Hello AFter 2 sleep", flush=True)
    return "hello"

  def connect(self, *args):
    return self.service.connect()
  
  def disconnect(self, *args):
    if self.service.connector:
        self.service.stop()
    return {"status": "disconnected"}

  def print(self, request, *args):
    return self.service.start_print(request.params)
  
  def prints(self, request, *args):
    # prnts = Print.select().order_by(Print.created_at.desc())
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    # print(f'request search params = {request.params}', flush=True)
    if request.params.get("q[name]"):
      print(f'request search params = {request.params.get("q[name]")}', flush=True)

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
    print(f"sync layerkeep {request.params}", flush=True)
    prnt = Print.get_by_id(print_id)
    if prnt.layerkeep_id:
      return {"data": prnt.json}
    
    response = await layerkeep.create_print({"data": {"print": prnt.json, "params": request.params}})

    if not response.success:
      raise response
    
    prnt.layerkeep_id = response.body.get("data").get("id")
    prnt.save()
    return {"data": prnt.json}

  async def unsync_print_from_layerkeep(self, request, print_id, *args):
    print(f"unsync layerkeep {request.params}", flush=True)
    prnt = Print.get_by_id(print_id)
    prnt.layerkeep_id = None
    prnt.save()
    return {"data": prnt.json}


  def delete_print(self, request, print_id, *args):
    prnt = Print.get_by_id(print_id)
    prnt.delete_instance(recursive=True)
    return {"success": True}

  def printer_commands(self, request, *args):
    # prnts = Print.select().order_by(Print.created_at.desc())    
    page = int(request.params.get("page") or 1)
    per_page = int(request.params.get("per_page") or 5)
    if request.params.get("print_id"):
      prnt = Print.get_by_id(request.params.get("print_id"))
      q = prnt.commands.order_by(PrinterCommand.created_at.desc())
    else:
      q = self.service.printer.commands.order_by(PrinterCommand.created_at.desc())
    
    # prnt = Print.get_by_id(print_id)
    # q = prnt.commands.order_by(PrinterCommand.created_at.desc())
    cnt = q.count()
    num_pages = math.ceil(cnt / per_page)
    return {"data": [p.to_json(recurse=False) for p in q.paginate(page, per_page)], "meta": {"current_page": page, "last_page": num_pages, "total": cnt}}
    # return self.service.start_print(request.params)
  
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


