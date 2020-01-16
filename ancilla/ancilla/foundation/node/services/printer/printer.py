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

class CommandQueue(object):

    def __init__(self):
        self.queue = OrderedDict()
        self.current_command = None
        self.current_expiry = None

    def add(self, cmd):
        self.queue.pop(cmd.identifier(), None)
        self.queue[cmd.identifier()] = cmd

    def get_command(self):
      if not self.current_command and len(self.queue) > 0:
        cid, cmd = self.queue.popitem(False)
        self.current_command = cmd
        self.current_expiry = time.time() + 5000
      return self.current_command 

    def finish_command(self, status="finished"):
      # print("FINISH Cmd", flush=True)
      if self.current_command:
        self.current_command.status = status
        self.current_command.save()
      self.current_command = None
      self.current_expiry = None

    def update_expiry(self):
        self.current_expiry = time.time() + 5000

    def clear(self):
      self.queue.clear()
      self.current_command = None
      self.current_expiry = None

    def __next__(self):
        address, worker = self.queue.popitem(False)
        return address
    

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
        self.command_queue = CommandQueue()

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


    # @property
    # def actions(self):
    #   return [
    #     "get_state",
    #     "command"
    #   ]
    def cleanup(self):
      print("printer cleanup", flush=True)
      if self.connector:
        self.connector.close()
      super().cleanup()

    def test_hook(self, *args):
      print(f"TESTHOOK Fired: {args}", flush=True)

    def start(self, *args):
      print("START Printer", flush=True)
      self.connector = SerialConnector(self.ctx, self.identity, self.printer.port, self.printer.baud_rate)
      # self.connector.start()
    
    def connect(self, *args):
      try:
        
        #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
        # else:

        print("INSIDE PRINTER CONNECT", flush=True)
        if not self.connector:
          self.start()
        res = self.connector.open()
        # if res["status"] == "success":
        self.connector.run()
        self.state.connected = True
        self.fire_event(PrinterEvent.connection.opened, {"status": "success"})
        return {"status": "connected"}
        # else:
        #   print("Printer Connect False", flush=True)
        #   self.state.connected = False
        #   self.fire_event(PrinterEvent.connection.failed, res)
        #   return res
      except Exception as e:
        print(f'Exception Open Conn: {str(e)}')
        self.state.connected = False
        self.fire_event(PrinterEvent.connection.failed, {"error": str(e)})
        raise AncillaError(400, {"error": str(e)})
        # return {"error": str(e), "status": "failed"}
        # self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    def stop(self, *args):
      print("Printer Stop", flush=True)
      res = self.connector.close()
      self.command_queue.clear()      
      self.state.connected = False
      self.fire_event(PrinterEvent.connection.closed, res)
      return res

    def close(self, *args):
      self.stop(args)


    def process_commands(self):
      # print("INSIDE PROCESS COMMANDS")
      cmd = self.command_queue.get_command()
      if not cmd:
        return
      
      # print(f"Process CMD {cmd.json}", flush=True)
      # request = cmd.request
      if cmd.status == "pending":
        cmd.status = "running"
        
        res = self.connector.write(cmd.command.encode('ascii'))
        err = res.get("error")
        if err:
          cmd.status = "error"
          cmd.response.append(err)
          self.command_queue.finish_command(status="error")
        elif cmd.nowait:
          self.command_queue.finish_command()
        else:
          cmd.save()
      elif cmd.status != "running":
        self.command_queue.finish_command(status=cmd.status)     
      else:
        # print(f"CMD is Running {cmd.command}", flush=True)
        IOLoop.current().add_callback(self.process_commands)

    # def add_print_command(self, parent_id, num, data, nowait=False, skip_queue=False, print_id=None):
      
    def add_command(self, parent_id, num, data, nowait=False, skip_queue=False, print_id=None):
      if type(data) == bytes:
        data = data.decode('utf-8')
      pc = PrinterCommand(parent_id=parent_id, sequence=num, command=data, printer_id=self.printer.id, nowait=nowait, print_id=print_id)
      pc.save(force_insert=True)

      # if data == "RUN SETUP":
      #   ct = CommandTask(pc)        
      #   self.task_queue.put(ct)
      if skip_queue:
        self.connector.write(pc.command.encode('ascii'))
      else:
        self.command_queue.add(pc)
        IOLoop.current().add_callback(self.process_commands)
      return pc


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


    def send_command(self, msg):
      payload = msg.get("data")
      # parent_id, num, data, nowait=False, skip_queue=False
      cmd = payload.get("cmd")
      skip_queue = (payload.get("skip_queue") or False)
      nowait = (payload.get("nowait") or False)
      if cmd.startswith(";"):
        nowait = True

      # print("CONNECT WRITE", data)
      # request = DeviceRequest.get_by_id(request_id)
      status = "success"
      reason = ""
      if not cmd.endswith('\n'):
        cmd = cmd + '\n'
      if self.connector.alive:
        self.add_command(0, 1, cmd, nowait, skip_queue)
      else:
        status = "failed"
        reason = "Not Connected"

      # request.state = status
      # request.save()
      return {"status": status, "reason": reason}

    def command(self, msg):
      cmd = msg.get("data")
      # print("CONNECT WRITE", data)
      # request = DeviceRequest.get_by_id(request_id)
      status = "success"
      reason = ""
      if not cmd.endswith('\n'):
        cmd = cmd + '\n'
      if self.connector.alive:
        self.add_command(0, 1, cmd)
      else:
        status = "failed"
        reason = "Not Connected"

      # request.state = status
      # request.save()
      return {"status": status, "reason": reason}


    def cancel_print(self, msg):
      print(f"STOP Printing {msg}", flush=True)      
      try:
        payload = msg.get('data') or {}
        task_name = payload.get("task_name")

        task_name = self.current_print.name #"print"        
        if self.current_task.get(task_name):
          self.current_task[task_name].cancel()
          
          return {"status": "success"}
        else:
          raise AncillaError(404, {"error": "Task Not Found"})
          # return {"status": "error", "error": "Task Not Found"}

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Cant cancel recording task {str(e)}", flush=True)
        raise AncillaError(400, {"error": f"Could not cancel task {str(e)}"})
        # return {"status": "error", "error": f"Could not cancel task {str(e)}"}

    def pause_print(self, msg, *args):
      try:
        payload = msg.get('data') or {}
        task_name = payload.get("task_name")


        # for k, v in self.current_task.items():
        #     print(f"TASKkey = {k} and v = {v}", flush=True)

        task_name = self.current_print.name #"print"        
        if self.current_task.get(task_name):
          self.current_task[task_name].pause()
          
          return {"status": "success"}
        else:
          raise AncillaError(404, {"error": "Task Not Found"})

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Can't pause print task {str(e)}", flush=True)
        raise AncillaError(400, {"error": f"Could not pause print {str(e)}"})

      # if self.current_task["print"]:
      #   self.current_task["print"].pause()
      # # if self.state == "printing":
      # #   self.state = "paused"
      # self.state.status = 'Idle'
      # self.state.printing = False
      # return {"status": }
    # def resume_print(self, data):
    #   try:
    #     payload = msg.get('data') or {}
    #     task_name = payload.get("task_name")


    #     # for k, v in self.current_task.items():
    #     #     print(f"TASKkey = {k} and v = {v}", flush=True)

    #     task_name = self.current_print.name #"print"        
    #     if self.current_task.get(task_name):
    #       self.current_task[task_name].pause()
          
    #       return {"status": "success"}
    #     else:
    #       raise AncillaError(404, {"error": "Task Not Found"})

    #   except AncillaResponse as e:
    #     raise e
    #   except Exception as e:
    #     print(f"Can't pause print task {str(e)}", flush=True)
    #     raise AncillaError(400, {"error": f"Could not pause print {str(e)}"})

    def start_print(self, data):
      try:
        # res = data.decode('utf-8')
        # payload = json.loads(res)
        # name = payload.get("name") or "PrintTask"
        if not self.state.connected:
          raise Exception("Printer Not Connected")

        if self.current_print and (self.current_print.status == "running" or self.current_print.status == "idle"):
          raise AncillaError(404, {"error": "There is already a print"})
          # return {"status": "error", "error": "There is already a print"}
        

        name = "print"
        print_id = data.get("print_id")
        self.current_print = None
        if print_id:
          prt = Print.get_by_id(print_id)
          if prt.status != "finished": # and prt.status != "failed":
            self.current_print = prt
          
            
        
        if not self.current_print:
          fid = data.get("file_id")
          if not fid:
            raise AncillaError(404, {"error": "No file to print"})
            # return {"status": "error", "error": "No file to print"}

          sf = PrintSlice.get(fid)  
          name = data.get("name") or f"print-{sf.name}"
          settings = data.get("settings") or {}
          
          self.current_print = Print(name=name, status="idle", settings=settings, printer_snapshot=self.record, printer=self.printer, print_slice=sf)
          self.current_print.save(force_insert=True)

          # name = prt.name
        # Print(name=name, status="running", printer_snapshot=device.record, printer=device.printer, slice_file=sf)
        pt = PrintTask(self.current_print.name, self, data)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(partial(self._process_tasks))

        return {"print": self.current_print}

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Cant Start Print task {str(e)}", flush=True)
        # return {"status": "error", "error": f"Cant Start Print task {str(e)}"}
        raise AncillaError(400, {"error": f"Cant Start Print task {str(e)}"})

      # return {"queued": "success"}

            
              
