'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
import importlib
# from ..zhelpers import zpipe

# import cv2

import os
import shutil

import json


# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
# from ...base_service import BaseService
# from ....utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest

# from queue import Queue
# import asyncio

from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
# from zmq.eventloop.ioloop import PeriodicCallback

# from zmq.asyncio import Context, ZMQEventLoop

from zmq.eventloop.zmqstream import ZMQStream
from tornado.ioloop import IOLoop, PeriodicCallback

import inspect
import asyncio
from types import CoroutineType

from tornado.platform.asyncio import AnyThreadEventLoopPolicy

import string, random

from ....data.models import Printer as PrinterModel
from ...base_service import BaseService
from .driver import SerialConnector

from ....data.models import PrinterCommand, PrintSlice, Print
# from queue import Queue

from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback


from ...tasks.ancilla_task import PeriodicTask
from ...tasks.print_task import PrintTask




# from ..tasks.device_task import PeriodicTask


from ...events import Event, EventPack, Service as EventService
from ...events.printer import Printer as PrinterEvent
from ...events.event_pack import EventPack
from ...middleware.printer_handler import PrinterHandler as PrinterDataHandler
from ...response import AncillaResponse, AncillaError
from ...request import Request

from ....utils.delegate import DelegatedAttribute

# from multiprocessing import Process, Lock, Pipe, Value, Array
# import multiprocessing as mp


def yields(value):
    return isinstance(value, asyncio.futures.Future) or inspect.isgenerator(value) or \
           isinstance(value, CoroutineType)

    # @asyncio.coroutine
    # def call_maybe_yield(func, *args, **kwargs):
    #     rv = func(*args, **kwargs)
    #     if yields(rv):
    #         rv = yield from rv
    #     return rv

async def call_maybe_yield(func, *args, **kwargs):
    rv = func(*args, **kwargs)
    if yields(rv):
        rv = await rv
    return rv


class CommandQueue(object):

    def __init__(self):
        self.queue = OrderedDict()
        self.current_command = None
        self.current_expiry = None
        self.callbacks = OrderedDict()

    def add(self, cmd, cb = None):
        self.queue.pop(cmd.identifier(), None)
        self.queue[cmd.identifier()] = cmd
        self.callbacks[cmd.identifier()] = cb

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
        # cb = self.callbacks[self.current_command.identifier()]
        cb = self.callbacks.pop(self.current_command.identifier(), None)
        if cb:
          res = cb(self.current_command.__data__)
          
        # self.current_command.save()
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
    


class PrinterHandler():
    # connector = None
    # endpoint = None         # Server identity/endpoint
    # identity = None
    # alive = True            # 1 if known to be alive
    # ping_at = 0             # Next ping at this time
    # expires = 0             # Expires at this time
    # state = "IDLE"
    # recording = False
    
    # command_queue = CommandQueue()
    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]
    connector = None
    current_print = None
    # zmq_pub = None
    # zmq_router = None

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
      
      print(f"Printer Connect {os.getpid()}", flush=True)
      self.connector = SerialConnector(self.process.ctx, self.process.identity, port, baud_rate)
      self.connector.open()
      
      self.connector.run()
      self.process.state.connected = True
      print(f"Printer {os.getpid()} ")
      # tcr = CameraRecording(task_name="bob", settings={}, status="pending")
      # tcr.save()
      self.fire_event(PrinterEvent.connection.opened, {"status": "success"})
      # self.process.fire_event(PrinterEvent.connection.opened, {"status": "success"})
      return {"status": "connected"}


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
        # else:
        #   cmd.save()
      elif cmd.status != "running":
        self.command_queue.finish_command(status=cmd.status)     
      else:
        # print(f"CMD is Running {cmd.command}", flush=True)
        IOLoop.current().add_callback(self.process_commands)

    def add_command(self, parent_id, num, data, nowait=False, skip_queue=False, print_id=None):
      if type(data) == bytes:
        data = data.decode('utf-8')
      pc = PrinterCommand(parent_id=parent_id, sequence=num, command=data, printer_id=self.printer.get("id"), nowait=nowait, print_id=print_id)
      # pc.save(force_insert=True)

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


    def start_print(self, data):
      print(f"START PRINTING {data}", flush=True)
      # print(f"RECORDING MSG: {json.dumps(msg, cls=ServiceJsonEncoder)}", flush=True)
      # return {"started": True}
      try:
        
        if self.current_print and (self.current_print.status == "running" or self.current_print.status == "idle"):
          raise AncillaError(404, {"error": "There is already a print"})

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
          
          # printer_snapshot = self.model.model.json
          self.current_print = Print(name=name, status="idle", settings=settings, printer_snapshot=self.printer, printer_id=self.printer.get("id"), print_slice=sf)
          self.current_print.save(force_insert=True)

          # name = prt.name
        # Print(name=name, status="running", printer_snapshot=device.record, printer=device.printer, slice_file=sf)
        pt = PrintTask(self.current_print.name, self, data)
        self.process.add_task(pt)

        return {"print": self.current_print.to_json()}
        # return {"status": "success", "task": name}

      except Exception as e:
        print(f"Cant record task {str(e)}", flush=True)
        raise AncillaError(400, {"status": "error", "error": f"Could not record {str(e)}"}, exception=e)
        # return {"status": "error", "error": f"Could not record {str(e)}"}

    def cancel_print(self, msg):
      print(f"STOP Printing {msg}", flush=True)      
      try:
        payload = msg.get('data') or {}
        task_name = payload.get("task_name")

        task_name = self.current_print.name #"print"        
        if self.process.current_task.get(task_name):
          self.process.current_task[task_name].cancel()
          
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
        if self.process.current_task.get(task_name):
          self.process.current_task[task_name].pause()
          
          return {"status": "success"}
        else:
          raise AncillaError(404, {"error": "Task Not Found"})

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Can't pause print task {str(e)}", flush=True)
        raise AncillaError(400, {"error": f"Could not pause print {str(e)}"})        




