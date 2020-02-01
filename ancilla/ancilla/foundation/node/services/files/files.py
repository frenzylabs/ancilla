import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop


from ....data.models import PrintSlice
from ...base_service import BaseService
from ...events.file import FileEvent
from ...api.file import FileApi
from ....env import Env

import asyncio
from functools import partial
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback




class FileService(BaseService):    
    # state = "IDLE"    
    __actions__ = ["delete_file"]

    # events = PrinterEvents
    def __init__(self, model, **kwargs):

        super().__init__(model, **kwargs)
        self.api = FileApi(self)
        self.event_class = FileEvent

        # self.state = Dotdict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })

        if not self.config.root_path:
          self.model.configuration["root_path"] = "/".join([Env.ancilla, self.model.id])
          self.model.save()
          self.config.update(self.model.configuration)
          
        if not os.path.exists(self.config.root_path):
          os.makedirs(self.config.root_path)

        print(f"the rootpath = {self.config.root_path}")

        # print(f"INSIDE PRINTER INIT = {self.identity}", flush=True)
        # self.register_data_handlers(PrinterHandler(self))

    @property
    def root_path(self):
      return self.config.root_path
            
    def delete_file(self, obj):
      if isinstance(obj, PrintSlice):
        sf = obj
      else:
        data = obj.get("data") or None
        if data:
          if data.get("id"):
            sf = PrintSlice.get_by_id(data.get("id"))            
      
      if sf:
        if os.path.exists(sf.path):
          os.remove(sf.path)
        res = sf.delete_instance(recursive=True)
        self.fire_event(FileEvent.deleted, {"file": sf.json})
        return True
      
      return False

    

              
