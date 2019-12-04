
import time
import zmq
from tornado.ioloop import IOLoop
from tornado.gen import coroutine
# from asyncio.coroutines import coroutine
from zmq.eventloop.zmqstream import ZMQStream

import importlib
import json
import asyncio
# import zmq.asyncio
import typing

from types import CoroutineType

from zmq.eventloop.future import Context

from playhouse.signals import Signal, post_save

from .app import App, yields, ConfigDict
from ..data.models import Camera, Printer, Service
from .api import NodeApi

class NodeService(App):
    __actions__ = []
    
    def __init__(self, identity=b'localhost'):
        super().__init__()
        self.identity = identity
        self.name = identity.decode('utf-8')
        # self.ctx = Context()
        self.ctx = zmq.Context()
        self.bind_address = "tcp://*:5556"
        self.router_address = "tcp://127.0.0.1:5556"

        self.zrouter = self.ctx.socket(zmq.ROUTER)
        self.zrouter.identity = self.identity
        self.zrouter.bind("tcp://*:5556")
        self.zmq_router = ZMQStream(self.zrouter, IOLoop.current())
        self.zmq_router.on_recv(self.router_message)
        self.zmq_router.on_send(self.router_message_sent)

        self.pubsocket = self.ctx.socket(zmq.PUB)
        self.pubsocket.bind("ipc://publisher")
        self.publisher = ZMQStream(self.pubsocket)

        # self.event_stream = self.ctx.socket(zmq.SUB)
        # self.event_stream.connect("ipc://publisher")
        # self.event_stream = ZMQStream(self.event_stream)
        # self.event_stream.on_recv(self.event_message)

        self.collectorsocket = self.ctx.socket(zmq.PULL)
        self.collectorsocket.bind("ipc://collector")
        self.collector = ZMQStream(self.collectorsocket)
        self.collector.on_recv(self.handle_collect)

        
        # for base in cls.__bases__:
        #     if hasattr(base, 'get_event'):
        #         res = base.get_event(base, name)
        #         if res:
        #           return res
        
        self._services = []
        self.init_services()
        
        self.api = NodeApi(self)

        post_save.connect(self.post_save_handler, name=f'service_model', sender=Service)
        # self.pipe, peer = zpipe(self.ctx)        
        # self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer))
        # self.agent.daemon = True
        # self.agent.name = f"Node{self.name}"
        # self.agent.start()
        # time.sleep(0.5) # Allow connection to come up


        # print(f'DEVICE NAME = {name}', flush=True)  
        # if type(name) == bytes:
        #   self.identity = name
        #   self.name = name.decode('utf-8')
        # else:
        #   self.name = name
        #   self.identity = name.encode('ascii')
        # self.data_handlers = []
        # self.task_queue = Queue()
        # self.current_task = {}
        # self.state = {}
        # self.events = []

        # self.data_stream.stop_on_recv()

    def list_actions(self, *args):
      return self.__actions__

    def mount_service(self, model):
      print("INSIDE MOUNT SERVICE")
      prefix = model.api_prefix #f"/services/{model.kind}/{model.id}/"
      res = next((item for item in self._mounts if item.config['_mount.prefix'] == prefix), None)
      if res:
        return ["exist", res]
      ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), model.class_name)  
      service = ServiceCls(model)
      self.mount(prefix, service)
      return ["created", service]

    def handle_name_change(self, oldname, newname):
      sc = Service.event_listeners.children().alias('children')
      services = Service.select().from_(Service, sc).where(sc.c.Key.startswith(oldname))[:]      
      for s in services:
        evhandlers = {}
        print(f"EVTservice= {s.json}", flush=True)
        for (k, v) in s.event_listeners.items():
          # print(f"EVT lISTNER: {k}")
          if k.startswith(oldname + "."):
            newkey = newname + k[len(oldname):]
            evhandlers[newkey] = v
          else:
            evhandlers[k] = v
        s.event_listeners = evhandlers
        s.save()

    # services = Service.update(Service.settings["event_handlers"].update(evhandlers)).where
    # .from_(Service, sc).where(sc.c.Key.startswith(oldname))[:]      
            
    def post_save_handler(self, sender, instance, *args, **kwargs):
      model = next((item for item in self._services if item.id == instance.id), None)
      
      if model:
        oldmodel = model
        srv = next((item for item in self._mounts if item.model.id == instance.id), None)
        # cur_settings = json.dumps(model.settings)
        # cur_events = json.dumps(model.event_listeners)
        print(f"POST SAVE SERVICE= args= {args} {srv}", flush=True)
        
        oldname = model.name
        model = instance
        print(f"OLDName = {oldname}, instan= {instance.name}", flush=True)
        if oldname != instance.name:
          print("Handle name change")
          self.handle_name_change(oldname, instance.name)
          
        if srv:
          # print(f"CURSETTINGS = {cur_settings}", flush=True)
          # print(f"ModelNEWSETTINGS = {json.dumps(model.settings)}", flush=True)
          
          # "name": "myend", 
          # curconfig = json.dumps(self.model.configuration)
          
          srv.model = model

          old_settings = srv.settings.to_json()
          old_event_listeners = srv.event_handlers.to_json()
          

          # print(f"NEWListeners = {json.dumps(srv.model.event_listeners)}", flush=True)
          # print(f"OldListeners = {json.dumps(oldmodel.event_listeners)}", flush=True)
          new_settings = ConfigDict().load_dict(srv.model.settings).to_json() 
          new_event_listeners = ConfigDict().load_dict(srv.model.event_listeners).to_json() 
          # if cur_settings != json.dumps(srv.model.settings):
          if old_settings != new_settings:
            
            srv.settings.update(new_settings)
            oldkeys = old_settings.keys()
            newkeys = new_settings.keys()
            for key in oldkeys - newkeys:
              if key not in srv.settings._virtual_keys:
                del srv.settings[key]
          if old_event_listeners != new_event_listeners:
            
            
            srv.event_handlers.update(new_event_listeners)
            # srv.event_handlers.update(srv.model.event_listeners)

            # print(f"NEWListeners = {srv.event_handlers.to_json()}", flush=True)
            print(f"OldListeners = {old_event_listeners}", flush=True)
            print(f"NEWListeners = {new_event_listeners}", flush=True)
            oldkeys = old_event_listeners.keys()            
            newkeys = new_event_listeners.keys()
            for key in oldkeys - newkeys:
              if key not in srv.settings._virtual_keys:
                del srv.event_handlers[key]
              # del srv.event_handlers[t]
              # self.event_stream.setsockopt(zmq.UNSUBSCRIBE, t.encode('ascii'))
            # for t in newkeys - oldkeys:
            # print(f"OldListeners = {oldevt}", flush=True)
            # srv.settings.update(srv.model.settings)
      #     self.fire_event(self.event_class.settings_changed, self.settings)

    def init_services(self):
      # Service.select().where(Service.settings['event_handlers']['y1'] == 'z1')
      # self.service_models = {"printers": {}, "cameras": {"id": 1}, "files": {}}
      # res = [c for c in Camera.select()]
      # for c in Camera.select():
      filemodel = Service.select().where(Service.kind == "file").first()
      if not filemodel:
        self.__create_file_service()
      
      lkmodel = Service.select().where(Service.kind == "layerkeep").first()
      if not lkmodel:
        self.__create_layerkeep_service()

      for s in Service.select():
        self._services.append(s)
        if s.kind == "file":          
          ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
          service = ServiceCls(s)      
          self.mount(f"/services/{s.kind}/{s.id}/", service)
        elif s.kind == "layerkeep":          
          ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
          service = ServiceCls(s) 
          self.mount(f"/services/{s.kind}/{s.id}/", service)
          
      # if not fileserviceexist:
        
      #   ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
      #   service = ServiceCls(s)
      #   self.mount(f"/services/{s.kind}s/{s.id}/", service)
      # filemodel = Service.select().where(Service.kind == "file").first()
      # if not filemodel:
      #   self.__create_file_service()

      #   filemodel = query.get()
      # else:
      #   filemodel = self.__create_file_service()
      
      # ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), filemodel.class_name)  
      # service = ServiceCls(filemodel)
      # # self.mount(f"/files<:re:\/?>", service)
      # # self.mount(f"/files/", service)
      # self.mount(f"/services/{filemodel.kind}/{filemodel.id}/", service)

      # # self.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
      # self.route('/services/<name><other:re:.*>', 'GET', self.catchIt)
      # ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services.camera"), "Camera")
      # service = ServiceCls("mbplocal")
      # self.mount(f"/services/cameras/1/", service)

      # for k, v in self.service_models.items():
      #   self.mount(f"/{k}/{v.id}/", v)
      
      # for service in Service.select():
      #     identifier = service.name.encode('ascii')
      #     self.service_models[service.id] = service
      # pass
      # self.mount()
    def __create_layerkeep_service(self):
      service = Service(name="layerkeep", kind="layerkeep", class_name="Layerkeep")
      service.save(force_insert=True)
      return service

    def __create_file_service(self):
      service = Service(name="local", kind="file", class_name="FileService")
      service.save(force_insert=True)
      return service

    # def __connect_service(self, identifier, model):
    #   try:
    #     ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), model.device_type)
    #     device = ServiceCls(self.ctx, identifier)
    #     device.start()
    #     time.sleep(0.1) # Allow connection to come up
    #     # print("CONNECT DEVICE", flush=True)
    #     self.active_devices[identifier] = device
    #     return device
    #   except Exception as e:
    #       print(f"EXception connecting to device {str(e)}", flush=True)
    #       raise Exception(f'Could Not Connect to Device: {str(e)}')
        

    def send(self, environ = {}, **kwargs):
      res = self._handle(environ)
      return res

    def run_action(self, action, payload, target = None, **kwargs):      
      print(f'Actions= {action}, payload={payload} and target ={target}')
      if not target:
        target = self
      else:
        target = next((item for item in self._mounts if item.name == target), self)
      
      print(f"target= {target} ", flush=True)
      try:
        if action in target.list_actions():
          method = getattr(target, action)
          res = method(payload)
          return res
        else:
          return {"status": "error", "message": "Action Doesnt Exist"}
      except Exception as e:
        return {"status": "error", "message": f'Error Running Action: {str(e)}' }
      

    def sendto(self, action):
      node_identity, request_id, device_identity, action, *msgparts = msg
      print("Unpack here", flush=True)
      # msg = msg[2]
      # if len(msg) > 2:
      #   subtree = msg[2]
      message = ""
      if len(msgparts) > 0:
        message = msgparts[0]

      print("DEVICE IDENTITY here", flush=True)
      response = {"request_id": request_id.decode('utf-8'), "action": action.decode('utf-8')}

      if device_identity:
        curdevice = self.active_devices.get(device_identity)
        if curdevice:
          res = curdevice.send([request_id, action, message])

    def router_message_sent(self, msg, status):
      print("INSIDE ROUTE MESSageSEND", flush=True)

    def router_message(self, msg):
      print("Unpack here", flush=True)
      print(f"Router Msg = {msg}", flush=True)
      
      replyto, method, path, *args = msg
      method = method.decode('utf-8')
      path = path.decode('utf-8')
      params = {}
      if len(args):
        try:
          params = json.loads(args.pop().decode('utf-8'))
        except Exception as e:
          print(f"Could not load params: {str(e)}", flush=True)
      
      environ = {"REQUEST_METHOD": method.upper(), "PATH": path, "params": params}
      res = self._handle(environ)
      # print(typing.co, flush=True)
      # if isinstance(res, CoroutineType):
      if yields(res):
        future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
        print("FUTURE = ", future)
        zmqrouter = self.zmq_router
        def onfinish(fut):
          newres = fut.result(1)
          status = b'success'
          if "error" in newres:
            status = b'error'
          zmqrouter.send_multipart([replyto, status, json.dumps(newres).encode('ascii')])

        future.add_done_callback(onfinish)

      else:
        print(f"THE RESP here = {res}", flush=True)
        status = b'success'
        if "error" in res:
          status = b'error'
        self.zmq_router.send_multipart([replyto, status, json.dumps(res).encode('ascii')])
      # node_identity, request_id, device_identity, action, *msgparts = msg
      return "Routed"


    # def request(self, request):
    #   pass

    def handle_collect(self, msg):
      self.publisher.send_multipart(msg)
      if len(msg) >= 3:
          topic, service, *other = msg
          # topic, device, payload, *other = msg
          if topic.startswith(b'events.'):
              # print(f"INSIDE HERE, {topic} and {device}", flush=True)
              # np = [device + b'.' + topic, device]
              # print(f"INSIDE HERE, {np}", flush=True)
              self.publisher.send_multipart([service + b'.' + topic, service] + other)
      pass

    def event_message(self, msg):
      print("event message")
      pass

    def service_change(self, *args):
      tree = Service.settings["event_handlers"].tree().alias('tree')
      Service.select().from_(Service, tree).where(tree.c.Key.startswith("servicename.events.print"))

      sc = Service.settings["event_handlers"].children().alias('children')      
      q = Service.select().from_(Service, sc).where(sc.c.Key.startswith("servicename.events.print"))

      q = (Service.select(sc.c.key, sc.c.value, sc.c.fullkey)
         .from_(Service, sc)
         .order_by(sc.c.key)
         .tuples())
      q[:]
