'''
 printer_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/29/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import logging
import sys
import time

import os

import json


from tornado.ioloop import IOLoop

from .driver import SerialConnector
from ....data.models import PrinterCommand, PrintSlice, Print

from ...tasks.print_task import PrintTask
from ...events.printer import Printer as PrinterEvent

from ...middleware.printer_handler import PrinterHandler as PrinterDataHandler
from ...response import AncillaResponse, AncillaError

from ....utils.delegate import DelegatedAttribute

from .command_queue import CommandQueue


class PrinterHandler():

    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]
    connector = None
    current_print = None

    def __init__(self, process, **kwargs): 
      self.process = process
      self.printer_data_handler = PrinterDataHandler(self)
      self.process.register_data_handlers(self.printer_data_handler)
      self.command_queue = CommandQueue()
        
    
    state = DelegatedAttribute('process', 'state')
    identity = DelegatedAttribute('process', 'identity')
    fire_event = DelegatedAttribute('process', 'fire_event')

    def close(self):
      if self.connector:
        self.connector.close()

      self.process.fire_event(PrinterEvent.connection.closed, {"status": "success"})
    

    def connect(self, data):
      printer = data.get("printer")
      port = printer.get("port")
      baud_rate = printer.get("baud_rate")
      self.printer = printer
      
      self.connector = SerialConnector(self.process.ctx, self.process.identity, port, baud_rate)
      self.connector.open()
      
      self.connector.run()
      self.process.state.connected = True
      self.fire_event(PrinterEvent.connection.opened, {"status": "success"})
      return {"status": "connected"}


    def process_commands(self):
      cmd = self.command_queue.get_next_command()
      if not cmd:
        # IOLoop.current().add_callback(self.process_commands)
        return

      if cmd.status == "pending":
        cmd.status = "running"
        
        res = self.connector.write(cmd.command.encode('ascii'))
        err = res.get("error")
        if err:
          cmd.status = "error"
          cmd.response.append(err)
          self.command_queue.finish_command(cmd, status="error")
        elif cmd.nowait:
          self.command_queue.finish_command(cmd)
      elif cmd.status != "running":
        self.command_queue.finish_command(cmd, status=cmd.status)     
      else:
        # print(f"CMD is Running {cmd.command}", flush=True)
        IOLoop.current().add_callback(self.process_commands)

    def add_command(self, parent_id, num, data, nowait=False, skip_queue=False, print_id=None):
      if type(data) == bytes:
        data = data.decode('utf-8')
      if not data.endswith('\n'):
        data = data + '\n'
      pc = PrinterCommand(parent_id=parent_id, sequence=num, command=data, printer_id=self.printer.get("id"), nowait=nowait, print_id=print_id)

      # if data == "RUN SETUP":
      #   ct = CommandTask(pc)        
      #   self.task_queue.put(ct)
      if skip_queue:
        self.connector.write(pc.command.encode('ascii'))
      else:
        self.command_queue.add(pc)
        IOLoop.current().add_callback(self.process_commands)
      return pc
      
    def send_command(self, msg):
      payload = msg.get("data")
      # parent_id, num, data, nowait=False, skip_queue=False
      cmd = payload.get("cmd")
      parent_id = payload.get("parent_id", 0) 
      skip_queue = (payload.get("skip_queue") or False)
      nowait = (payload.get("nowait") or False)
      if cmd.startswith(";"):
        nowait = True


      status = "success"
      reason = ""
      if not cmd.endswith('\n'):
        cmd = cmd + '\n'
      if self.connector.alive:
        self.add_command(parent_id, 1, cmd, nowait, skip_queue)
      else:
        status = "failed"
        reason = "Not Connected"

      return {"status": status, "reason": reason}


    def start_print(self, data):
      if self.current_print and (self.current_print.status == "running" or self.current_print.status == "idle"):
          raise AncillaError(404, {"error": "There is already a print"})

      try:
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

          sf = PrintSlice.get(fid)  
          name = data.get("name") or f"print-{sf.name}"
          settings = data.get("settings") or {}
          
          self.current_print = Print(name=name, status="idle", settings=settings, printer_snapshot=self.printer, printer_id=self.printer.get("id"), print_slice=sf)
          self.current_print.save(force_insert=True)


        pt = PrintTask(self.current_print.name, self, data)
        self.process.add_task(pt)

        return {"print": self.current_print.to_json()}

      except Exception as e:
        raise AncillaError(400, {"status": "error", "error": f"Could not print {str(e)}"}, exception=e)


    def cancel_print(self, msg):

      try:
        payload = msg.get('data') or {}
        task_name = payload.get("task_name")

        task_name = self.current_print.name #"print"        
        if self.process.current_tasks.get(task_name):
          self.process.current_tasks[task_name].cancel()
          
          return {"status": "success"}
        else:
          raise AncillaError(404, {"error": "Task Not Found"})

      except AncillaResponse as e:
        raise e
      except Exception as e:
        raise AncillaError(400, {"error": f"Could not cancel task {str(e)}"})

    def pause_print(self, msg, *args):
      try:
        payload = msg.get('data') or {}
        task_name = payload.get("task_name")

        task_name = self.current_print.name #"print"        
        if self.process.current_tasks.get(task_name):
          self.process.current_tasks[task_name].pause()
          
          return {"status": "success"}
        else:
          raise AncillaError(404, {"error": "Task Not Found"})

      except AncillaResponse as e:
        raise e
      except Exception as e:
        raise AncillaError(400, {"error": f"Could not pause print {str(e)}"})




