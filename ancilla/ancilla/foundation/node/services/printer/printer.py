'''
 printer.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
import zmq
import os

import json
from tornado.ioloop import IOLoop


from ....data.models import Printer as PrinterModel
from ...base_service import BaseService

from ....data.models import PrinterCommand, PrintSlice, Print

from tornado.queues     import Queue


from ...tasks.periodic_task import PeriodicTask

from ...events.printer import Printer as PrinterEvent
from ...api.printer import PrinterApi
from ...middleware.printer_handler import PrinterHandler
from ...response import AncillaError, AncillaResponse

from ...request import Request

from ...service_connector import ServiceConnector
from .printer_handler import PrinterHandler as ProcessPrinterHandler


    

class Printer(BaseService):    

    __actions__ = [
        "command",
        "send_command",
        "start_print",
        "cancel_print",
        "pause_print"
      ]

    # events = PrinterEvents
    def __init__(self, model, **kwargs):
        super().__init__(model, **kwargs)
        self.print_queued = False
        self.current_print = None
        self.task_queue = Queue()
        self.command_queue = None 

        self.printer = PrinterModel.get(PrinterModel.service == model)

        temp_settings = self.model.settings.get("tempReporting")
        if not temp_settings:
          self.model.settings["tempReporting"] = {
            "enabled": True,
            "strategy": "poll",
            "interval": "5"
          }
          self.model.save()
          self.settings.load_dict(self.model.settings)

        self.record = self.printer.json
        self.api = PrinterApi(self)
        self.event_class = PrinterEvent
        self.connector = None


        
        self.state.load_dict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "printing": False
        })
        
        # self.register_data_handlers(PrinterHandler(self))

        key = b"events.printer.state.changed"
        self.event_stream.setsockopt(zmq.SUBSCRIBE, key)

        

    async def make_request(self, request):
      return await self.connector.make_request(request)

    def cleanup(self):
      if self.connector:
        self.connector.stop()
      super().cleanup()

    def test_hook(self, data, layerkeep, **kwargs):
      pass
      # print(f"TESTHOOK Fired: lk = {layerkeep} {kwargs}", flush=True)
      

    def start(self, *args):
      if not self.connector:
        self.connector = ServiceConnector(self, ProcessPrinterHandler)
        
      self.connector.start()
      self.connector.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'data')

    
    async def connect(self, *args):
      if not self.connector or not self.connector.is_alive():
        self.start()

      printer = self.model.model
      request = Request({"action": "connect", "body": {"printer": printer.to_json()}})
      try:
        res =  await self.make_request(request)
        self.state.connected = True
        return res
      except Exception as e:   
        print(f"connect Exception =  {str(e)}")
        self.connector.stop()
        self.connector = None
        raise e

      return res

    async def stop(self, *args):
      if self.connector:
        self.connector.stop()
        self.connector = None

      # self.command_queue.clear()
      self.state.connected = False
      self.fire_event(PrinterEvent.connection.closed, self.state)
      return {"success": True}

    async def close(self, *args):
      await self.stop(args)

    def update_model(self, service_model):
        return super().update_model(service_model)

    def cancel(self, task_id, *args):
      if self.current_task["print"]:
        self.current_task["print"].cancel(task_id)

      self.state.status = 'Idle'
      self.state.printing = False
      return {"state": self.state}
      

    def periodic(self, data):
      try:
        res = data.decode('utf-8')
        payload = json.loads(res)
        name = payload.get("name") or "PeriodicTask"
        method = payload.get("method")
        timeinterval = payload.get("interval")
        pt = PeriodicTask(name, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(self._process_tasks)

      except Exception as e:
        print(f"Cant periodic task {str(e)}", flush=True)


    async def send_command(self, msg):
      if not self.state.connected:
        raise AncillaError(400, {"error": "Printer Not Connected"})

      request = Request({"action": "send_command", "body": msg})
      res =  await self.make_request(request)
      return res


    async def cancel_print(self, msg):
      # print(f"STOP RECORDING {msg}", flush=True)
      try:
        
        if not self.connector:
          self.state.printing = False
          print_id = msg.get("data", {}).get("print_id")
          if print_id:
            prnt = Print.get_by_id(print_id)
            prnt.status = "cancelled"
            prnt.save()
            return AncillaResponse({"print": prnt.to_json()})
          return AncillaError(404, {"error": "Print Not Found"})
        else:
          request = Request({"action": "cancel_print", "body": msg})
          res =  await self.make_request(request)
          self.state.printing = False
          return res

      except AncillaResponse as e:
        raise e
      except Exception as e:
        raise AncillaError(400, {"error": f"Cant Cancel Print {str(e)}"})

      # except Exception as e:
      #   print(f"Cant cancel print task {str(e)}", flush=True)
      #   return {"status": "error", "error": f"Could not cancel print {str(e)}"}



    async def pause_print(self, msg, *args):
      try:
        if not self.connector:
          self.state.printing = False
        request = Request({"action": "pause_print", "body": msg})
        res =  await self.make_request(request)
        self.state.printing = False
        return res

      except Exception as e:
        print(f"Cant pause print task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not pause task {str(e)}"}

      

    async def start_print(self, data):
      try:
        if not self.state.connected:
          raise Exception("Printer Not Connected")
      
        # request = {"action": "start_recording", "body": msg}
        request = Request({"action": "start_print", "body": data})
        res =  await self.make_request(request)
        self.state.printing = True
        return res

      except AncillaResponse as e:
        raise e
      except Exception as e:
        raise AncillaError(400, {"error": f"Cant Start Print task {str(e)}"})



              
