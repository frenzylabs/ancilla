import threading
import time
import sys
import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio
import json

from tornado.ioloop import IOLoop
from ..zhelpers import zpipe
from ...data.models import Printer, Print, SliceFile, DeviceRequest
# from .devices import *
from tornado.gen        import sleep
from .device_task import DeviceTask


class PrintTask(DeviceTask):
  def __init__(self, name, request_id, payload, *args):
    super().__init__(name, *args)
    self.request_id = request_id
    self.payload = payload
    self.state = "pending"
    # ["wessender", "start_print", {"name": "printit", "file_id": 1}]


  async def run(self, device):
    request = DeviceRequest.get_by_id(self.request_id)
    sf = None
    num_commands = -1
    try:
      # print(f"CONTENT = {content}", flush=True)
      fid = self.payload.get("file_id")
      sf = SliceFile.get(fid)
      device.current_print = Print(status="running", request_id=request.id, printer_snapshot=device.record, printer=device.printer, slice_file=sf)
      device.current_print.save(force_insert=True)          
      # num_commands = file_len(sf.path)
    except Exception as e:
      print(f"Cant get file to print {str(e)}", flush=True)
      # request.status = "failed"
      # request.save()
      # self.publish_request(request)
      return

    self.state = "running"
    

    try:
      with open(sf.path, "r") as fp:
        cnt = 1
        fp.seek(0, os.SEEK_END)
        endfp = fp.tell()
        # print("End File POS: ", endfp)
        fp.seek(0)
        line = fp.readline()
        lastpos = 0
        while self.state == "running":
          # for line in fp:
          pos = fp.tell()
          
          # print("File POS: ", pos)
          if pos == endfp:
            self.state = "finished"
            # request.status = "finished"
            # request.save()
            device.current_print.status = "finished"
            device.current_print.save()
            break

          if not line.strip():
            line = fp.readline()
            continue

          print("Line {}, POS: {} : {}".format(cnt, pos, line))    

          is_comment = line.startswith(";")
          self.current_command = device.add_command(self.request_id, cnt, line, is_comment)

          print(f"CurCmd: {self.current_command.command}", flush=True)
          
          while (self.current_command.status == "pending" or self.current_command.status == "running"):
            await sleep(0.1)
            if self.state != "running":
              break

          
          if self.current_command.status == "error":
            request.status = "failed"
            request.save()
            self.state = "print_failed"
            break

          if self.current_command.status == "finished":
            device.current_print.state["pos"] = pos
            device.current_print.save()
            line = fp.readline()
            cnt += 1                  

        
    except Exception as e:
      device.current_print.status = "failed"
      device.current_print.save()
      self.state = "failed"
      print(f"Print Exception: {str(e)}", flush=True)

    print(f"FINISHED PRINT {self.state}", flush=True)
    device.print_queued = False
    device.current_print = None
    return {"state": self.state}
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