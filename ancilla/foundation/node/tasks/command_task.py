import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio
import json

from tornado.ioloop import IOLoop
from zmq.eventloop.ioloop import PeriodicCallback
# from ..zhelpers import zpipe
from ...data.models import Print, SliceFile

import functools
from tornado.gen        import sleep
from .ancilla_task import AncillaTask

from ...utils import Dotdict

from ..events.printer import Printer

class CommandTask(AncillaTask):
  def __init__(self, name, payload, *args):
    super().__init__(name, *args)
    # self.request_id = request_id    
    self.payload = payload
    # self.state = Dotdict({"status": "pending", "model": {}})
    self.state.update({"status": "pending", "model": {}})
    # self.state._add_change_listener(
    #         functools.partial(self.trigger_hook, 'state'))

    # ["wessender", "start_print", {"name": "printit", "file_id": 1}]

  @property
  def status(self):
    return self.state.status

  @status.setter
  def status(self, value):
    self.state.status = value

  # def status(self):
  #   return self.state.status

  async def run(self, service):
    self.service = service
    try:
      # print(f"CONTENT = {content}", flush=True)
      command = self.payload.get("command")
      # name = self.payload.get("commands") or ["M105", "M109 S60"]
      # sf = SliceFile.get(fid)
      commands = ["M105", "M109 S60"]
      

      self.state.status = "running"

      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant get file to print {str(e)}", flush=True)
      # device.fire_event(Printer.print.failed, {"status": "failed", "reason": str(e)})
      # request.status = "failed"
      # request.save()
      # self.publish_request(request)
      return

    self.state.status = "running"
    

    try:
        cmdIndex = 0
        totalCmds = len(commands)
        
        while self.state.status == "running":
          # for line in fp:
          
          
          # print("File POS: ", pos)
          if cmdIndex == totalCmds :
            self.state.status = "finished"
            # request.status = "finished"
            # request.save()
            # device.current_print.status = "finished"
            # device.current_print.save()
            break

          cmd = commands[cmdIndex]
          if not cmd.endswith('\n'):
            cmd += '\n'


          # print("Line {}: {}".format(cmdIndex, cmd))    

          is_comment = cmd.startswith(";")
          self.current_command = self.service.add_command(self.task_id, cmdIndex, cmd, is_comment)

          # print(f"CurCmd: {self.current_command.command}", flush=True)
          
          while (self.current_command.status == "pending" or 
                self.current_command.status == "running" or 
                self.current_command.status == "busy"):
            await sleep(0.1)
            if self.state.status != "running":
              self.current_command.status = self.state.status
              break

          print(f'InsidePrintTask curcmd= {self.current_command}', flush=True)
          if self.current_command.status == "error":
            # request.status = "failed"
            # request.save()
            device.current_print.status = "failed"
            self.state.status = "failed"
            self.state.reason = "Could Not Execute Command: " + self.current_command.command
            break

          if self.current_command.status == "finished":            
            cmdIndex += 1                  

        
    except Exception as e:
      # device.current_print.save()
      self.state.status = "failed"
      self.state.reason = str(e)
      print(f"Print Exception: {str(e)}", flush=True)

    
    

    print(f"FINISHED Command Task {self.state}", flush=True)
    
    # self.state_callback.stop()
    # device.fire_event(Printer.print.state.changed, self.state)
    # self.device.state.printing = False
    # self.device.fire_event(Printer.state.changed, self.device.state)
    return {"state": self.state}

  def cancel(self, task_id):
    self.state.status = "cancelled"
    # self.device.add_command(request_id, 0, 'M0\n', True, True)

  def pause(self):
    self.state.status = "paused"

  def get_state(self):
    print("get state", flush=True)
    st = self.state.json
    return st
    # self.state.model = self.device.current_print.json
    # if st != self.state.json:
    #   self.device.fire_event(Printer.print.state.changed, self.state)
    
    # self.publish_request(request)
  

# class PeriodicTask(DeviceTask):
#   def __init__(self, name, request_id, *args, **kwargs):
#     super().__init__(name, *args)  
#     self.interval = kwargs.get("interval") or 2000
#     self.io_loop = IOLoop.current()    
#     self.state = "initialized"
#     self.run_count = 0
#     self.run_timeout = None

#   async def run(self):
#     print(f"RUN PERIODIC TASK {self.name}", flush=True)
#     if self.state == "initialized":
#       self._next_timeout = time.time() + self.interval / 1000.0
#       self.run_timeout = self.io_loop.add_timeout(self._next_timeout, self.run)
#       self.state = "pending"
#     elif self.state == "running":
#       print("still running")
#       pass
#     elif self.state == "pending":
      
#       self.state = "running"
#       print("is running now", flush=True)
#       time.sleep(2)
#       self.state = "pending"
#       self._next_timeout = time.time() + self.interval / 1000.0
#       self.run_timeout = self.io_loop.add_timeout(self._next_timeout, self.run)
#     else:
#       self.run_timeout.cancel()
#     return "task"

#   def stop(self):
#     self.state = "finished"
#     if self.run_timeout:
#       self.run_timeout.cancel()
#     # if self.state == ""





# # class CommandQueue(object):
# #     current_command = None
# #     current_expiry = None

# #     def __init__(self):
# #         self.queue = OrderedDict()

# #     def add(self, cmd):
# #         self.queue.pop(cmd.identifier(), None)
# #         self.queue[cmd.identifier()] = cmd

# #     def get_command(self):
# #       if not self.current_command:
# #         cid, cmd = self.queue.popitem(False)
# #         self.current_command = cmd
# #         self.current_expiry = time.time() + 5000
# #       return self.current_command 

# #     def finish_command(self, status="finished"):
# #       if self.current_command:
# #         self.current_command.status = status
# #         self.current_command.save()
# #       self.current_command = None
# #       self.current_expiry = None

# #     def update_expiry(self):
# #         self.current_expiry = time.time() + 5000

# #     def __next__(self):
# #         address, worker = self.queue.popitem(False)
# #         return address
        
# # class Device(object):
# #     endpoint = None         # Server identity/endpoint
# #     identity = None
# #     alive = True            # 1 if known to be alive
# #     ping_at = 0             # Next ping at this time
# #     expires = 0             # Expires at this time
# #     workers = []
# #     data_handlers = []
# #     request_handlers = []
# #     interceptors = []
# #     data_stream = None
# #     input_stream = None
# #     pusher = None

# #     def __init__(self, ctx, name, **kwargs):    
# #         print(f'DEVICE NAME = {name}', flush=True)  
# #         self.identity = name
# #         # self.ping_at = time.time() + 1e-3*PING_INTERVAL
# #         # self.expires = time.time() + 1e-3*SERVER_TTL

# #         self.ctx = ctx #zmq.Context()

# #         self.pusher = self.ctx.socket(zmq.PUSH)
# #         self.pusher.connect(f"ipc://collector")

# #         # self.ctx = zmq.Context()
# #         deid = f"inproc://{self.identity}_collector"
# #         self.data_stream = self.ctx.socket(zmq.PULL)
# #         # print(f'BEFORE CONNECT COLLECTOR NAME = {deid}', flush=True)  
# #         self.data_stream.bind(deid)
# #         time.sleep(0.1)        
# #         self.data_stream = ZMQStream(self.data_stream)
# #         # self.data_stream.stop_on_recv()

# #         self.input_stream = self.ctx.socket(zmq.ROUTER)
# #         # print(f"ipc://{self.identity.decode('utf-8')}_taskrouter", flush=True)
# #         input_url = f"ipc://{self.identity.decode('utf-8')}_taskrouter"
# #         # input_url = f"tcp://*:5558"
# #         self.input_stream.identity = f"{self.identity.decode('utf-8')}_input".encode('ascii')  #self.identity #b"printer"
# #         self.input_stream.bind(input_url)
# #         time.sleep(0.1)

# #         self.input_stream = ZMQStream(self.input_stream)
# #         # self.input_stream.on_recv(self.on_message)
# #         # self.input_stream.on_send(self.input_sent)
# #         IOLoop.current().add_callback(self.start_receiving)
# #         # sys.stderr.flush()


# #     def start_receiving(self):
# #       # print("Start receiving", flush=True)
# #       self.data_stream.on_recv(self.on_data)
# #       # self.input_stream.on_recv(self.on_message)

# #     def register_data_handlers(self, obj):
# #       data_handlers.append(obj)

# #     def input_sent(self, msg, status):
# #       print("INPUT SENT", msg)

# #     def on_message(self, msg):
# #       print("ON MESSGE", msg)

# #     def on_tada(self, *args):
# #       print("ON TADA", flush=True)

# #     def on_data(self, data):
# #       # print("ON DATA", data)
# #       self.pusher.send_multipart(data)

# #     def stop(self):
# #       print("stop")
    
# #     def start(self):
# #       print("RUN SERVER", flush=True)

# #     def send(self, msg):
# #       print("DEvice Send", flush=True)
# #       print(msg)
# #       # self.pipe.send_multipart([b"COMMAND", msg])


# #     # def ping(self, socket):
# #     #     if time.time() > self.ping_at:
# #     #         print("SEND PING FOR %s", self.identity)
# #     #         socket.send_multipart([self.identity, b'PING', b'/'])
# #     #         self.ping_at = time.time() + 1e-3*PING_INTERVAL
# #     #     else:
# #     #       print("NO PING: %s  ,  %s ", time.time(), self.ping_at)

# #     # def tickless(self, tickless):
# #     #     if tickless > self.ping_at:
# #     #         tickless = self.ping_at
# #     #     return tickless