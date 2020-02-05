import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop


from ....data.models import Printer as PrinterModel
from ...base_service import BaseService
from .driver import SerialConnector

from ....data.models import PrinterCommand, PrintSlice, Print
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback

import functools

from ...tasks.ancilla_task import PeriodicTask
from ...tasks.print_task import PrintTask

from ...events.printer import Printer as PrinterEvent
from ...api.printer import PrinterApi
from ...middleware.printer_handler import PrinterHandler
from ...app import ConfigDict
from ...response import AncillaError, AncillaResponse

from ...request import Request

from ...service_connector import ServiceConnector
from .printer_handler import PrinterHandler as ProcessPrinterHandler

# class CommandQueue(object):

#     def __init__(self):
#         self.queue = OrderedDict()
#         self.current_command = None
#         self.current_expiry = None
#         self.callbacks = OrderedDict()

#     def add(self, cmd, cb = None):
#         self.queue.pop(cmd.identifier(), None)
#         self.queue[cmd.identifier()] = cmd
#         self.callbacks[cmd.identifier()] = cb

#     def get_command(self):
#       if not self.current_command and len(self.queue) > 0:
#         cid, cmd = self.queue.popitem(False)
#         self.current_command = cmd
#         self.current_expiry = time.time() + 5000
#       return self.current_command 

#     def finish_command(self, status="finished"):
#       # print("FINISH Cmd", flush=True)
#       if self.current_command:
#         self.current_command.status = status
#         # cb = self.callbacks[self.current_command.identifier()]
#         cb = self.callbacks.pop(self.current_command.identifier(), None)
#         if cb:
#           res = cb(self.current_command.__data__)
          
#         # self.current_command.save()
#       self.current_command = None
#       self.current_expiry = None

#     def update_expiry(self):
#         self.current_expiry = time.time() + 5000

#     def clear(self):
#       self.queue.clear()
#       self.current_command = None
#       self.current_expiry = None

#     def __next__(self):
#         address, worker = self.queue.popitem(False)
#         return address
    

class Printer(BaseService):    
    # ping_at = 0             # Next ping at this time
    # expires = 0             # Expires at this time
    # workers = []
    # state = "IDLE"
    
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
        self.command_queue = None #CommandQueue()

        self.printer = PrinterModel.get(PrinterModel.service == model)
        # self.printer = model #query[0]
        self.record = self.printer.json
        self.api = PrinterApi(self)
        self.event_class = PrinterEvent
        self.connector = None
        # self.state = Dotdict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        print(f"Printerevent {PrinterEvent.settings_changed.value()}", flush=True)
        
        self.state.load_dict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "printing": False
        })
        
        print(f"INSIDE PRINTER INIT = {self.identity}", flush=True)
        self.register_data_handlers(PrinterHandler(self))

        key = b"events.printer.state.changed"
        self.event_stream.setsockopt(zmq.SUBSCRIBE, key)

        

    # @property
    # def actions(self):
    #   return [
    #     "get_state",
    #     "command"
    #   ]
    async def make_request(self, request):
      return await self.connector.make_request(request)

    def cleanup(self):
      print("printer cleanup", flush=True)
      if self.connector:
        self.connector.stop()
      super().cleanup()

    def test_hook(self, data, layerkeep, **kwargs):
      print(f"TESTHOOK Fired: lk = {layerkeep} {kwargs}", flush=True)
      #print(f", andkwar= {kwargs}", flush=True)

    def start(self, *args):
      print("START Printer", flush=True)
      if not self.connector:
        self.connector = ServiceConnector(self, ProcessPrinterHandler)
        
      self.connector.start()
      self.connector.process_event_stream.setsockopt(zmq.SUBSCRIBE, b'data')
      # self.connector.process_event_stream.setsockopt(zmq.SUBSCRIBE, self.identity + b'.data')

      # printer = self.model.model
      # self.connector = SerialConnector(self.ctx, self.identity, printer.port, printer.baud_rate)
      # self.connector.start()
    
    async def connect(self, *args):
      print("printer connect", flush=True)
      if not self.connector or not self.connector.is_alive():
        self.start()

      printer = self.model.model
      # request = Request({"action": "connect", "body": {"port": printer.port, "baud_rate": printer.baud_rate}})
      request = Request({"action": "connect", "body": {"printer": printer.to_json()}})
      try:
        res =  await self.make_request(request)
        print(f'res = {res}')
        self.state.connected = True
        return res
      except Exception as e:   
        print(f"connect Exception =  {str(e)}")
        # await self.close()
        self.connector.stop()
        self.connector = None
        raise e

      return res

    async def stop(self, *args):
      print("Printer Stop", flush=True)
      if self.connector:
        self.connector.stop()
        self.connector = None

      # self.command_queue.clear()
      self.state.connected = False
      self.fire_event(PrinterEvent.connection.closed, self.state)
      return {"success": True}

    async def close(self, *args):
      await self.stop(args)


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
      print(f'PRINTER PLUGINS = {self.plugins}')
      if not self.state.connected:
        raise AncillaError(400, {"error": "Printer Not Connected"})
      
      print("send command", flush=True)
      # request = {"action": "get_or_create_video_processor", "body": {"endpoint": self.model.model.endpoint}}
      request = Request({"action": "send_command", "body": msg})
      res =  await self.make_request(request)
      return res




    # def send_command(self, msg):
    #   payload = msg.get("data")
    #   # parent_id, num, data, nowait=False, skip_queue=False
    #   cmd = payload.get("cmd")
    #   skip_queue = (payload.get("skip_queue") or False)
    #   nowait = (payload.get("nowait") or False)
    #   if cmd.startswith(";"):
    #     nowait = True

    #   # print("CONNECT WRITE", data)
    #   # request = DeviceRequest.get_by_id(request_id)
    #   status = "success"
    #   reason = ""
    #   if not cmd.endswith('\n'):
    #     cmd = cmd + '\n'
    #   if self.connector.is_alive():
    #     self.add_command(0, 1, cmd, nowait, skip_queue)
    #   else:
    #     status = "failed"
    #     reason = "Not Connected"

    #   # request.state = status
    #   # request.save()
    #   return {"status": status, "reason": reason}

    # def command(self, msg):
    #   cmd = msg.get("data")
    #   # print("CONNECT WRITE", data)
    #   # request = DeviceRequest.get_by_id(request_id)
    #   status = "success"
    #   reason = ""
    #   if not cmd.endswith('\n'):
    #     cmd = cmd + '\n'
    #   if self.connector.alive:
    #     self.add_command(0, 1, cmd)
    #   else:
    #     status = "failed"
    #     reason = "Not Connected"

    #   # request.state = status
    #   # request.save()
    #   return {"status": status, "reason": reason}

    async def cancel_print(self, msg):
      # print(f"STOP RECORDING {msg}", flush=True)      
      # print(f"STOPRECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      try:
        print("cancel print record", flush=True)
        request = Request({"action": "cancel_print", "body": msg})
        res =  await self.make_request(request)
        print(f'stopprint = {res}')
        self.state.printing = False
        return res

      except Exception as e:
        print(f"Cant cancel print task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    # def cancel_print(self, msg):
    #   print(f"STOP Printing {msg}", flush=True)      
    #   try:
    #     payload = msg.get('data') or {}
    #     task_name = payload.get("task_name")

    #     task_name = self.current_print.name #"print"        
    #     if self.current_task.get(task_name):
    #       self.current_task[task_name].cancel()
          
    #       return {"status": "success"}
    #     else:
    #       raise AncillaError(404, {"error": "Task Not Found"})
    #       # return {"status": "error", "error": "Task Not Found"}

    #   except AncillaResponse as e:
    #     raise e
    #   except Exception as e:
    #     print(f"Cant cancel recording task {str(e)}", flush=True)
    #     raise AncillaError(400, {"error": f"Could not cancel task {str(e)}"})
    #     # return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    async def pause_print(self, msg, *args):
      try:
        print("pause print 1", flush=True)
        request = Request({"action": "pause_print", "body": msg})
        res =  await self.make_request(request)
        print(f'pause_print = {res}')
        self.state.printing = False
        return res

      except Exception as e:
        print(f"Cant pause print task {str(e)}", flush=True)
        return {"status": "error", "error": f"Could not pause task {str(e)}"}

      

    async def start_print(self, data):
      try:
        # res = data.decode('utf-8')
        # payload = json.loads(res)
        # name = payload.get("name") or "PrintTask"

        if not self.state.connected:
          raise Exception("Printer Not Connected")
      
        print("start print1", flush=True)
        # request = {"action": "start_recording", "body": msg}
        request = Request({"action": "start_print", "body": data})
        res =  await self.make_request(request)
        print(f'startprint = {res}')
        self.state.printing = True
        return res


        # return {"print": self.current_print}

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Cant Start Print task {str(e)}", flush=True)
        # return {"status": "error", "error": f"Cant Start Print task {str(e)}"}
        raise AncillaError(400, {"error": f"Cant Start Print task {str(e)}"})

      # return {"queued": "success"}

            
              
