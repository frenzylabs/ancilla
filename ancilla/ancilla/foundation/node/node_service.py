'''
 node_service.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/14/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import time
import zmq
from tornado.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

import importlib
import json
import asyncio
# import zmq.asyncio
import typing
import os, shutil
import uuid
import functools

from zmq.eventloop.future import Context

from playhouse.signals import Signal, post_save, post_delete
import atexit

import resource, psutil, signal, gc

from .app import App
from ..utils import yields
from ..utils.dict import ConfigDict
from ..data.models import Camera, Printer, Service, CameraRecording, Node
from .events.camera import Camera as CameraEvent
from .api import NodeApi
from ..env import Env
from .discovery.discovery import Discovery


class NodeService(App):
    __actions__ = []
    # _api_port = 5000


    def __init__(self, api_port=5000):
        super().__init__()        
        # self.api_port = api_port
        self.__api_port = api_port

        nodemodel = Node.select().first()
        if not nodemodel:
          settings = {"discovery": True, "discoverable": True}
          nodemodel = Node(uuid=uuid.uuid4().hex, settings=settings)
          nodemodel.node_name = "Ancilla"
          nodemodel.save(force_insert=True)
        self.model = nodemodel
        self.identity = self.model.uuid.encode('utf-8')
        self.name = self.model.name #identity.decode('utf-8')

        self.config.update({
            "catchall": True
        })

        self.settings = self.config._make_overlay()
        self.settings.load_dict(self.model.settings)

        self.ctx = zmq.Context.instance()

        self.setup_router()

        self.discovery = Discovery(self)


        self.settings._add_change_listener(
            functools.partial(self.settings_changed, 'settings'))
        

        # self.pubsocket = self.ctx.socket(zmq.PUB)
        # self.pubsocket.bind("ipc://publisher")
        # self.publisher = ZMQStream(self.pubsocket)
        publisher = self.ctx.socket(zmq.PUB)
        publisher.setsockopt( zmq.LINGER, 0 )
        # publisher.setsockopt(zmq.DONTWAIT, True)
        publisher.bind("ipc://publisher.ipc")
        self.publisher = ZMQStream(publisher)
        

        collector = self.ctx.socket(zmq.PULL)
        collector.bind("ipc://collector.ipc")
        collector.setsockopt( zmq.LINGER, 1 )
        self.collector = ZMQStream(collector)
        self.collector.on_recv(self.handle_collect)

        
        self.file_service = None
        self.layerkeep_service = None
        self._services = []
        self.init_services()
        
        self.api = NodeApi(self)

        post_save.connect(self.post_save_handler, name=f'service_model', sender=Service)
        post_delete.connect(self.post_delete_service_handler, name=f'camera_model', sender=Service)
        post_save.connect(self.post_save_node_handler, name=f'node_model', sender=Node)
        # post_delete.connect(self.post_delete_camera_handler, name=f'camera_model', sender=Camera)

        self.limit_memory()
        soft, hard = resource.getrlimit(resource.RLIMIT_AS) 
        print(f'Node MEM limit NOW = {soft}, {hard}')
        


    def _hangle_sig_memory(self, signum, stack):
      print("node service handle memory sig")
      gc.collect()


    def limit_memory(self): 
      maxhard = psutil.virtual_memory().available
      maxsoft = maxhard
      p = psutil.Process(pid=os.getpid())
      soft, hard = resource.getrlimit(resource.RLIMIT_AS) 
      if hard > 0:
        h = min([maxhard, hard])
      else:
        h = maxhard
      if h > 0:
        s = min([maxsoft, h])
      else:
        s = maxsoft

      if hasattr(p, 'rlimit'):
        # soft, hard = p.rlimit(resource.RLIMIT_AS) 
        print(f'Node MEM limit = {soft}, {hard}: {h}')
        
        p.rlimit(resource.RLIMIT_AS, (s, h))
      else:
        
        print(f'Node MEM limit = {soft}, {hard}:  {h}')
        resource.setrlimit(resource.RLIMIT_AS, (s, h))
      self._old_usr1_hdlr = signal.signal(signal.SIGUSR1, self._hangle_sig_memory)

    

    def cleanup(self):
      print('Clean Up Node and Services')
      for s in self._mounts:
        s.cleanup()
      self._mounts = []
      self.discovery.stop()      
      self.file_service = None
      self.layerkeep_service = None
      self.zmq_router.close()
      self.collector.close(linger=1)
      self.publisher.close(linger=1)
      self.ctx.destroy()


    @property
    def api_port(self):
        return self.__api_port

    @api_port.setter
    def api_port(self, value):
      self.discovery.update_port(value)
      self.__api_port = value
    

    def setup_router(self):
      trybind = 30
      bound = False
      self.router_port = 5556
      self.bind_address = "tcp://*:5556"
      self.router_address = "tcp://127.0.0.1:5556"

      zrouter = self.ctx.socket(zmq.ROUTER)
      zrouter.identity = self.identity

      while not bound and trybind > 0:
        try:
          self.bind_address = f"tcp://*:{self.router_port}"
          
          zrouter.bind(self.bind_address)
          self.router_address = f"tcp://127.0.0.1:{self.router_port}"
          print(f"Node Bound to {self.bind_address}")
          bound = True
        except zmq.error.ZMQError:
          trybind -= 1
          self.router_port += 1
      

      self.zmq_router = ZMQStream(zrouter, IOLoop.current())
      self.zmq_router.on_recv(self.router_message)
      self.zmq_router.on_send(self.router_message_sent)


    def list_actions(self, *args):
      return self.__actions__

    def list_plugins(self):
      import os
      for module in os.listdir(os.path.dirname(__file__)):
        if module == '__init__.py' or module[-3:] != '.py':
          continue
        __import__(module[:-3], locals(), globals())

    def mount_service(self, model):
      prefix = model.api_prefix #f"/services/{model.kind}/{model.id}/"
      res = next((item for item in self._mounts if item.config['_mount.prefix'] == prefix), None)
      if res:
        return ["exist", res]
      LayerkeepCls = getattr(importlib.import_module("ancilla.foundation.node.plugins"), "LayerkeepPlugin")    
      ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), model.class_name)  
      service = ServiceCls(model)
      service.install(LayerkeepCls())
      self._services.append(model)
      self.mount(prefix, service)
      return ["created", service]

    def handle_service_name_change(self, oldname, newname):
      sc = Service.event_listeners.children().alias('children')
      services = Service.select().from_(Service, sc).where(sc.c.Key.startswith(oldname))[:]      
      for s in services:
        evhandlers = {}
        for (k, v) in s.event_listeners.items():
          if k.startswith(oldname + "."):
            newkey = newname + k[len(oldname):]
            evhandlers[newkey] = v
          else:
            evhandlers[k] = v
        s.event_listeners = evhandlers
        s.save()

    # services = Service.update(Service.settings["event_handlers"].update(evhandlers)).where
    # .from_(Service, sc).where(sc.c.Key.startswith(oldname))[:]      
    def settings_changed(self, event, oldval, key, newval):
      # print(f'evt: {event} key= {key}  OldVal = {oldval}  NewVal: {newval}')
      if key == "discovery":
        self.discovery.run(newval)
      elif key == "discoverable":
        self.discovery.make_discoverable(newval)
      pass

    def post_save_node_handler(self, sender, instance, *args, **kwargs):
      print(f"Post save Node handler {sender}", flush=True)
      if self.model.name != self.name:
        self.name = instance.name
        self.discovery.update_name(self.name)
      
      old_settings = self.settings.to_json()
      new_settings = ConfigDict().load_dict(self.model.settings).to_json() 
      if old_settings != new_settings:
        # print(f"OldSet = {old_settings}", flush=True)
        # print(f"NEWSet = {new_settings}", flush=True)
        self.settings.update(new_settings)
        oldkeys = old_settings.keys()
        newkeys = new_settings.keys()
        for key in oldkeys - newkeys:
          if key not in self.settings._virtual_keys:
            del self.settings[key]


    def post_save_handler(self, sender, instance, *args, **kwargs):
      print(f"Post save Service handler {sender} {instance}", flush=True)
      model = None
      for idx, item in enumerate(self._services):
        if item.id == instance.id:
            model = item
            self._services[idx] = instance
      
      if model:
        oldmodel = model
        srv = next((item for item in self._mounts if item.model.id == instance.id), None)
        print(f'srv = {srv}')
        oldname = model.name
        model = instance
        # print(f"PostSaveHandler OLDName = {oldname}, instan= {instance.name}", flush=True)
        if oldname != instance.name:
          self.handle_service_name_change(oldname, instance.name)
          
        if srv:
          srv.update_model(model)

          old_config = ConfigDict().load_dict(oldmodel.configuration).to_json() 
          # old_config = oldmodel.configuration
          old_settings = srv.settings.to_json()
          old_event_listeners = srv.event_handlers.to_json()
          

          
          # print(f"NEWListeners = {json.dumps(srv.model.event_listeners)}", flush=True)
          # print(f"OldListeners = {json.dumps(oldmodel.event_listeners)}", flush=True)
          new_config = ConfigDict().load_dict(srv.model.configuration).to_json() 
          new_settings = ConfigDict().load_dict(srv.model.settings).to_json() 
          new_event_listeners = ConfigDict().load_dict(srv.model.event_listeners).to_json() 
          # if cur_settings != json.dumps(srv.model.settings):
          

          if old_config != new_config:
            # print(f"OldConfig = {old_config}", flush=True)
            # print(f"NEWConfig = {new_config}", flush=True)  
            # print(f"ConfVke {srv.config._virtual_keys}", flush=True)
            srv.config.update(new_config)
            oldkeys = old_config.keys()
            newkeys = new_config.keys()
            for key in oldkeys - newkeys:
              if key not in srv.config._virtual_keys:                
                del srv.config[key]

          if old_settings != new_settings:
            # print(f"OldSet = {old_settings}", flush=True)
            # print(f"NEWSet = {new_settings}", flush=True)
            # print(f"SettingsVke {srv.settings._virtual_keys}", flush=True)
            srv.settings.update(new_settings)
            oldkeys = old_settings.keys()
            newkeys = new_settings.keys()
            for key in oldkeys - newkeys:
              if key not in srv.settings._virtual_keys:
                del srv.settings[key]

          if old_event_listeners != new_event_listeners:            
            srv.event_handlers.update(new_event_listeners)

            # print(f"OldListeners = {old_event_listeners}", flush=True)
            # print(f"NEWListeners = {new_event_listeners}", flush=True)
            oldkeys = old_event_listeners.keys()            
            newkeys = new_event_listeners.keys()
            for key in oldkeys - newkeys:
              if key not in srv.settings._virtual_keys:
                del srv.event_handlers[key]


    def post_delete_service_handler(self, sender, instance, *args, **kwargs):
      # service_path = "/".join([Env.ancilla, "services", f"service{instance.id}"])
      if os.path.exists(instance.directory):
          shutil.rmtree(instance.directory)
      # self.delete_recording(instance)


    # def post_delete_camera_handler(self, sender, instance, *args, **kwargs):
    #   service_id = instance.service_id
    #   cam_path = "/".join([Env.ancilla, "services", f"service{instance.service_id}"])
    #   if os.path.exists(cam_path):
    #       shutil.rmtree(cam_path)


    def init_services(self):
      LayerkeepCls = getattr(importlib.import_module("ancilla.foundation.node.plugins"), "LayerkeepPlugin")    
      self.install(LayerkeepCls())
      lkmodel = Service.select().where(Service.kind == "layerkeep").first()
      if not lkmodel:
        self.__create_layerkeep_service()

      filemodel = Service.select().where(Service.kind == "file").first()
      if not filemodel:
        self.__create_file_service()
      

      for s in Service.select():
        self._services.append(s)
        if s.kind == "file":
          ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
          service = ServiceCls(s)      
          service.install(LayerkeepCls())
          self.file_service = service
          self.mount(f"/api/services/{s.kind}/{s.id}/", service)
        elif s.kind == "layerkeep":          
          ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
          service = ServiceCls(s) 
          self.layerkeep_service = service
          self.mount(f"/api/services/{s.kind}/{s.id}/", service)
        else:
          ServiceCls = getattr(importlib.import_module("ancilla.foundation.node.services"), s.class_name)  
          service = ServiceCls(s)      
          service.install(LayerkeepCls())
          self.mount(f"/api/services/{s.kind}/{s.id}/", service)
          
    def delete_service(self, service):
      self._services = [item for item in self._services if item.id != service.id]
      srv = next((item for item in self._mounts if item.model.id == service.id), None)
      if srv:
        self.unmount(srv)

    def delete_recording(self, msg):
      if isinstance(msg, CameraRecording):
        recording = msg
      else:
        data = msg.get("data") or None
        if data:
          if data.get("id"):
            recording = CameraRecording.get_by_id(data.get("id"))     
      
      if recording:
        try:
          
          if os.path.exists(recording.image_path):
            shutil.rmtree(recording.image_path)
          if os.path.exists(recording.video_path):
            shutil.rmtree(recording.video_path)

          res = recording.delete_instance(recursive=True)
          return True
        except Exception as e:
          print(f"delete exception {str(e)}")
          raise e
      
      return False

    def stop_service(self, service):
      srv = next((item for item in self._mounts if item.model.id == service.id), None)
      if srv:
        self.unmount(srv)

    def unmount(self, app):
      curmounts = self._mounts
      curmounts.remove(app)
      self.reset_app()
      self.api.setup()
      print("reseting app ", flush=True)
      app.cleanup()
      self.remount_apps(curmounts)
        
      
    def __create_layerkeep_service(self):
      service = Service(name="layerkeep", kind="layerkeep", class_name="Layerkeep")
      service.save(force_insert=True)
      return service

    def __create_file_service(self):
      service = Service(name="local", kind="file", class_name="FileService")
      service.save(force_insert=True)
      return service

    def send(self, environ = {}, **kwargs):
      res = self._handle(environ)
      return res

    def run_action(self, action, payload, target = None, **kwargs):      
      
      if not target:
        target = self
      else:
        target = next((item for item in self._mounts if item.name == target), self)
      
      # print(f'Actions= {action}, payload={payload} and target ={target}')
      try:
        if action in target.list_actions():
          method = getattr(target, action)
          res = method(payload)
          if yields(res):
            future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
            # while not future.done():
            #   time.sleep(0.01)
            # return future.result(0.)

            # print("FUTURE = ", future)
            # zmqrouter = self.zmq_router
            # def onfinish(fut):
            #   newres = fut.result(1)
            #   status = b'success'
            #   if "error" in newres:
            #     status = b'error'
            #   zmqrouter.send_multipart([replyto, status, json.dumps(newres).encode('ascii')])

            # future.add_done_callback(onfinish)

          else:
            return res  

        else:
          return {"status": "error", "message": "Action Doesnt Exist"}
      except Exception as e:
        return {"status": "error", "message": f'Error Running Action: {str(e)}' }
      

    def sendto(self, action):
      node_identity, request_id, device_identity, action, *msgparts = msg

      # msg = msg[2]
      # if len(msg) > 2:
      #   subtree = msg[2]
      message = ""
      if len(msgparts) > 0:
        message = msgparts[0]

      response = {"request_id": request_id.decode('utf-8'), "action": action.decode('utf-8')}

      if device_identity:
        curdevice = self.active_devices.get(device_identity)
        if curdevice:
          res = curdevice.send([request_id, action, message])

    def router_message_sent(self, msg, status):
      print("NODE INSIDE ROUTE MESSageSEND", flush=True)

    def router_message(self, msg):
      print("NOde Unpack here", flush=True)
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

      if yields(res):
        future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
        
        zmqrouter = self.zmq_router
        def onfinish(fut):
          newres = fut.result(1)
          status = b'success'
          if "error" in newres:
            status = b'error'
          zmqrouter.send_multipart([replyto, status, json.dumps(newres).encode('ascii')])

        future.add_done_callback(onfinish)

      else:
        status = b'success'
        if "error" in res:
          status = b'error'
        self.zmq_router.send_multipart([replyto, status, json.dumps(res).encode('ascii')])
      # node_identity, request_id, device_identity, action, *msgparts = msg
      return "Routed"


    # def request(self, request):
    #   pass

    def handle_collect(self, msg):
      # print(f'HandleCol Pub to {msg}', flush=True)
      self.publisher.send_multipart(msg)
      if len(msg) >= 3:
          topic, service, *other = msg
          # topic, device, payload, *other = msg
          if topic.startswith(b'events.'):
              # print(f"INSIDE HERE, {topic} and {device}", flush=True)
              self.publisher.send_multipart([service + b'.' + topic, service] + other)
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
