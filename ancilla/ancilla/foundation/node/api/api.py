
import time
import zmq
from tornado.ioloop import IOLoop
from zmq.eventloop.zmqstream import ZMQStream

import importlib
import json
import asyncio
# import zmq.asyncio

from zmq.eventloop.future import Context

# from .app import App
from ...data.models import Service, ServiceAttachment
from ..response import AncillaError


class Api(object):
    
    def __init__(self, service):
        self.service = service                
        self.setup()

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

    def setup(self, prefix = ""):
      self.service.route(f'{prefix}/settings', 'GET', self.settings)
      self.service.route(f'{prefix}/actions', 'GET', self.actions)
      self.service.route(f'{prefix}/routes', 'GET', self.routes)
      self.service.route(f'{prefix}/events', 'GET', self.events)
      self.service.route(f'{prefix}/attachments/<attachment_id>', 'DELETE', self.delete_attachment)
      self.service.route(f'{prefix}/attachments', 'POST', self.add_attachment)
      self.service.route(f'{prefix}/attachments', 'GET', self.attachments)

    def settings(self, *args):
      return {"settings": self.service.settings.to_json()}

    def routes(self, *args):
      return {"routes": [f"{r}" for r in self.service.routes]}

    def actions(self, *args):      
      return {"actions": self.service.list_actions()}
    
    def events(self, *args):
      print(f"THE EVENT DICT = {self.service.event_class.event_dict()}", flush=True)
      return {"events": self.service.event_class.list_events()}      

    def delete_attachment(self, request, attachment_id, *args, **kwargs):
      # attachment = self.service.model.service_attachments.where(ServiceAttachment.attachment_id == service_id).first()
      attachment = self.service.model.service_attachments.where(ServiceAttachment.id == attachment_id).first()
      if attachment:
        attachment.delete_instance()        
        return {"sucess": "Removed Attachment"}

      raise AncillaError(404, {"error": "No Attachment Found"})
      # return {"status": 404, "error": "No Attachment Found"}
      
    def add_attachment(self, request, *args):
      service_id = request.params.get("service_id")
      
      res = self.service.model.service_attachments.where(ServiceAttachment.attachment_id == service_id).first()
      if res:
        return {"attachment": res.json}
        
      attachment = Service.get_by_id(service_id)
      sa = ServiceAttachment(parent=self.service.model, attachment=attachment)
      sa.save()
      return {"attachment": sa.json}

    def attachments(self, *args):
      return {"attachments": [a.json for a in self.service.model.service_attachments]}

    def update_attachment(self, request, attachment_id, *args):
      pass

    # def init_services(self):
    #   self.service_models = {"printers": {}, "cameras": {}, "files": {}}
    #   for k, v in self.service_models.items():
    #     self.mount(f"/{k}/", v)
      
    #   # for service in Service.select():
    #   #     identifier = service.name.encode('ascii')
    #   #     self.service_models[service.id] = service
    #   # pass
    #   # self.mount()
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
        

    # def router_message_sent(self, msg, status):
    #   print("INSIDE ROUTE MESSageSEND", flush=True)

    # def router_message(self, msg):
    #   print("Unpack here", flush=True)
    #   print(f"Router Msg = {msg}", flush=True)
      
    #   replyto, method, path, *args = msg
    #   method = method.decode('utf-8')
    #   path = path.decode('utf-8')
    #   res = self._handle(method, path, {})
    #   print(f"THE RESP here = {res}", flush=True)
    #   self.zmq_router.send_multipart([replyto, b'tada', json.dumps(res).encode('ascii')])
    #   # node_identity, request_id, device_identity, action, *msgparts = msg
      
    #   pass


    # # def request(self, request):
    # #   pass

    # def handle_collect(self, msg):
    #   print("handle collect")
    #   pass

    # def event_message(self, msg):
    #   print("event message")
    #   pass
