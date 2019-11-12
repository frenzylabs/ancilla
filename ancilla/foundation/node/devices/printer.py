import threading
import time
import zmq
import os

import json
from tornado.ioloop import IOLoop

from ..zhelpers import zpipe, socket_set_hwm
from ...data.models import Printer as PrinterModel
from ..device import Device
from .serial_connector import SerialConnector
from ...env import Env
from ...data.models import DeviceRequest, PrinterCommand, SliceFile, Print
# from queue import Queue
import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback


from ..tasks.device_task import PeriodicTask
from ..tasks.print_task import PrintTask

from .middleware import PrinterHandler
from ...utils import Dotdict

class CommandQueue(object):
    current_command = None
    current_expiry = None

    def __init__(self):
        self.queue = OrderedDict()

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
      print("FINISH Cmd", flush=True)
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
    

class Printer(Device):
    connector = None
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time
    workers = []
    # state = "IDLE"
    print_queued = False
    current_print = None
    task_queue = Queue()
    command_queue = CommandQueue()

    def __init__(self, ctx, name, **kwargs):
        query = PrinterModel.select().where(PrinterModel.name == name).limit(1)
        self.printer = query[0]
        self.record = query[0].json
        self.port = self.record['port']
        self.baud_rate = self.record['baud_rate']



        
        super().__init__(ctx, name, **kwargs)

        self.state = Dotdict({
          "status": "Idle",
          "connected": False, 
          "alive": False,
          "printing": False
        })

        print(f"INSIDE PRINTER INIT = {self.identity}", flush=True)
        self.register_data_handlers(PrinterHandler(self))



    def start(self, *args):
      print("START Printer", flush=True)
      self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
      # self.connector.start()
    
    def connect(self, *args):
      try:
        # if not self.connector:
        #   self.connector = SerialConnector(self.ctx, self.identity, self.port, self.baud_rate)
        # else:
        print("INSIDE PRINTER CONNECT", flush=True)
        res = self.connector.open()
        if res["status"] == "success":
          print("Printer Connect", flush=True)
          self.connector.run()
          self.state.connected = True
          self.fire_event("connection.opened", {"status": "success"})
          return {"status": "connected"}
        else:
          print("Printer Connect False", flush=True)
          self.state.connected = False
          self.fire_event("connection.failed", res)
          return res
      except Exception as e:
        print(f'Exception Open Conn: {str(e)}')
        self.fire_event("connection.failed", {"error": str(e)})
        return {"error": str(e), "status": "failed"}
        # self.pusher.send_multipart([self.identity, b'error', str(e).encode('ascii')])

    def stop(self, *args):
      print("Printer Stop", flush=True)
      res = self.connector.close()
      self.command_queue.clear()      
      self.state.connected = False
      self.fire_event("connection.closed", res)
      return res

    def close(self, *args):
      self.stop(args)
    # def serialcmd(self, *args):
    #   cmd = args[0]

    # def reset(self, *args):
    #   s = self.connector.serial
    #   # s._reconfigurePort()
    #   # s.setDTR(True) # Drop DTR
    #   # time.sleep(0.022)    # Read somewhere that 22ms is what the UI does.
    #   # s.setDTR(True)

    # def flush(self, *args):
    #   self.connector.serial.flush()

    # def sendbreak(self, *args):
    #   print(f'break = serial = {self.connector.serial}', flush=True)
    #   self.connector.serial.break_condition
    #   self.connector.serial.send_break(1.0)
    #   print(self.connector.serial.break_condition)

    # def resetinput(self, *args):
    #   print(f'serial = {self.connector.serial}', flush=True)
    #   self.connector.serial.reset_input_buffer()

    # def resetoutput(self, *args):
    #   print(f'serial = {self.connector.serial}', flush=True)
    #   self.connector.serial.reset_output_buffer()      

    # def close(self, *args):
    #   print("Printer Close", flush=True)
    #   self.connector.close()

    # def on_message(self, msg):
    #   print("ON MESSAge", msg)  
      # identifier, request_id, cmd, *data = msg

    def process_commands(self):
      # print("INSIDE PROCESS COMMANDS")
      cmd = self.command_queue.get_command()
      if not cmd:
        return
      
      print(f"Process CMD {cmd.command}", flush=True)
      # request = cmd.request
      if cmd.status == "pending":
        cmd.status = "running"
        
        res = self.connector.write(cmd.command.encode('ascii'))
        err = res.get("error")
        print(f"CMD response: {res}")
        if err:
          print(f"CMD ERR response: {err}")
          cmd.status = "error"
          cmd.response.append(err)
          self.command_queue.finish_command(status="error")
        elif cmd.nowait:
          self.command_queue.finish_command()
        else:
          cmd.save()        
      else:
        print(f"CMD is Running {cmd.command}", flush=True)
        IOLoop.current().add_callback(self.process_commands)

    def add_command(self, request_id, num, data, nowait=False, skip_queue=False):
      if type(data) == bytes:
        data = data.decode('utf-8')
      pc = PrinterCommand(request_id=request_id, sequence=num, command=data, printer_id=self.record["id"], nowait=nowait)
      pc.save(force_insert=True)
      if skip_queue:
        self.connector.write(pc.command.encode('ascii'))
      else:
        self.command_queue.add(pc)
        IOLoop.current().add_callback(self.process_commands)
      return pc


    def get_state(self, *args):
      # print(self.connector.serial)
      serialopen = False
      if self.connector and self.connector.serial:
        serialopen = self.connector.serial.is_open
        self.state.connected = True
        self.state.status = 'Ready'
      else:
        self.state.connected = False
        self.state.status = 'Disconnected'

      return self.state

      # return {"open": serialopen, "alive": self.connector.alive, "state": self.state }

    def pause(self, *args):
      if self.current_task["print"]:
        self.current_task["print"].pause()
      # if self.state == "printing":
      #   self.state = "paused"
      self.state.status = 'Idle'
      self.state.printing = False
      return {"state": self.state}

    def cancel(self, request_id, *args):
      if self.current_task["print"]:
        self.current_task["print"].cancel(request_id)

      self.state.status = 'Idle'
      self.state.printing = False
      return {"state": self.state}
      

    def periodic(self, request_id, data):
      try:
        res = data.decode('utf-8')
        payload = json.loads(res)
        name = payload.get("name") or "PeriodicTask"
        method = payload.get("method")
        timeinterval = payload.get("interval")
        pt = PeriodicTask(name, request_id, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(self._process_tasks)

      except Exception as e:
        print(f"Cant periodic task {str(e)}", flush=True)


    def command(self, request_id, data):
      # print("CONNECT WRITE", data)
      request = DeviceRequest.get_by_id(request_id)
      status = "success"
      reason = ""
      if self.connector.alive:
        self.add_command(request_id, -1, data+b'\n')
      else:
        status = "success"
        reason = "Not Connected"

      request.state = status
      request.save()
      return {"status": status, "reason": reason}


    def start_print(self, request_id, data):
      try:
        res = data.decode('utf-8')
        payload = json.loads(res)
        # name = payload.get("name") or "PrintTask"
        method = payload.get("method")
        pt = PrintTask("print", request_id, payload)
        self.task_queue.put(pt)
        loop = IOLoop().current()
        loop.add_callback(partial(self._process_tasks))

      except Exception as e:
        print(f"Cant Start Print task {str(e)}", flush=True)

      return {"queued": "success"}


    def publish_request(self, request):
      rj = json.dumps(request.json).encode('ascii')
      self.pusher.send_multipart([self.identity+b'.request', b'request', rj])
            
              
