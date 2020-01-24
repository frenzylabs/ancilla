import threading
import time
import sys
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio

from tornado.ioloop import IOLoop
from tornado.gen        import sleep
from functools import partial

from ...data.models import Printer
from ..app import ConfigDict


global TASK_ID
TASK_ID = 0

class AncillaTask(object):
  def __init__(self, name, *args):
      global TASK_ID
      self.name = name
      TASK_ID += 1
      self.task_id = TASK_ID
      # self.state = ConfigDict()
      self.state = ConfigDict()._make_overlay()
        

  def run(self):
    return



class PeriodicTask(AncillaTask):
  def __init__(self, name, payload, *args, **kwargs):
    super().__init__(name, *args)  
    self.interval = kwargs.get("interval") or 3000
    # self.request_id = request_id
    self.io_loop = IOLoop.current()    
    self.state = "initialized"    
    self.run_count = 0
    self.run_timeout = None
    self.payload = payload


  async def run(self, device):
    print(f"RUN PERIODIC TASK {self.name}", flush=True)
    if self.state == "initialized":
      self._next_timeout = time.time() + self.interval / 1000.0
      self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run, device))
      self.state = "pending"
    elif self.state == "running":
      print("still running")
      pass
    elif self.state == "pending":
      self.run_count += 1
      self.state = "running"
      print("is running now", flush=True)
      await self.run_callback(device)

      self.state = "pending"
      self._next_timeout = time.time() + self.interval / 1000.0
      self.run_timeout = self.io_loop.add_timeout(self._next_timeout, partial(self.run, device))
    else:
      self.run_timeout.cancel()
    return "task"

  async def run_callback(self, device):
    cnt = 0
    try:
      cmd = self.payload.get("method")
      print(f"CMD {cmd}", flush=True)
      self.current_command = device.add_command(self.task_id, cnt, cmd.encode('ascii'))
      while self.command_active():
        await sleep(0.01)
        # if self.current_command == "pending":
        IOLoop.current().add_callback(device.process_commands)

      return {"status": self.current_command.status}

    except Exception as e:
      print(f"Couldnot run task {self.name}: {str(e)}")
      return {"status": "error", "reason": "Error Running Task"}

  def command_active(self):
    if self.state == "running" and (
        self.current_command.status == "pending" or 
        self.current_command.status == "running"):
        return True
    return False


  def stop(self):
    self.state = "finished"
    if self.run_timeout:
      self.run_timeout.cancel()
    # if self.state == ""





# class CommandQueue(object):
#     current_command = None
#     current_expiry = None

#     def __init__(self):
#         self.queue = OrderedDict()

#     def add(self, cmd):
#         self.queue.pop(cmd.identifier(), None)
#         self.queue[cmd.identifier()] = cmd

#     def get_command(self):
#       if not self.current_command:
#         cid, cmd = self.queue.popitem(False)
#         self.current_command = cmd
#         self.current_expiry = time.time() + 5000
#       return self.current_command 

#     def finish_command(self, status="finished"):
#       if self.current_command:
#         self.current_command.status = status
#         self.current_command.save()
#       self.current_command = None
#       self.current_expiry = None

#     def update_expiry(self):
#         self.current_expiry = time.time() + 5000

#     def __next__(self):
#         address, worker = self.queue.popitem(False)
#         return address
        
# class Device(object):
#     endpoint = None         # Server identity/endpoint
#     identity = None
#     alive = True            # 1 if known to be alive
#     ping_at = 0             # Next ping at this time
#     expires = 0             # Expires at this time
#     workers = []
#     data_handlers = []
#     request_handlers = []
#     interceptors = []
#     data_stream = None
#     input_stream = None
#     pusher = None

#     def __init__(self, ctx, name, **kwargs):    
#         print(f'DEVICE NAME = {name}', flush=True)  
#         self.identity = name
#         # self.ping_at = time.time() + 1e-3*PING_INTERVAL
#         # self.expires = time.time() + 1e-3*SERVER_TTL

#         self.ctx = ctx #zmq.Context()

#         self.pusher = self.ctx.socket(zmq.PUSH)
#         self.pusher.connect(f"ipc://collector")

#         # self.ctx = zmq.Context()
#         deid = f"inproc://{self.identity}_collector"
#         self.data_stream = self.ctx.socket(zmq.PULL)
#         # print(f'BEFORE CONNECT COLLECTOR NAME = {deid}', flush=True)  
#         self.data_stream.bind(deid)
#         time.sleep(0.1)        
#         self.data_stream = ZMQStream(self.data_stream)
#         # self.data_stream.stop_on_recv()

#         self.input_stream = self.ctx.socket(zmq.ROUTER)
#         # print(f"ipc://{self.identity.decode('utf-8')}_taskrouter", flush=True)
#         input_url = f"ipc://{self.identity.decode('utf-8')}_taskrouter"
#         # input_url = f"tcp://*:5558"
#         self.input_stream.identity = f"{self.identity.decode('utf-8')}_input".encode('ascii')  #self.identity #b"printer"
#         self.input_stream.bind(input_url)
#         time.sleep(0.1)

#         self.input_stream = ZMQStream(self.input_stream)
#         # self.input_stream.on_recv(self.on_message)
#         # self.input_stream.on_send(self.input_sent)
#         IOLoop.current().add_callback(self.start_receiving)
#         # sys.stderr.flush()


#     def start_receiving(self):
#       # print("Start receiving", flush=True)
#       self.data_stream.on_recv(self.on_data)
#       # self.input_stream.on_recv(self.on_message)

#     def register_data_handlers(self, obj):
#       data_handlers.append(obj)

#     def input_sent(self, msg, status):
#       print("INPUT SENT", msg)

#     def on_message(self, msg):
#       print("ON MESSGE", msg)

#     def on_tada(self, *args):
#       print("ON TADA", flush=True)

#     def on_data(self, data):
#       # print("ON DATA", data)
#       self.pusher.send_multipart(data)

#     def stop(self):
#       print("stop")
    
#     def start(self):
#       print("RUN SERVER", flush=True)

#     def send(self, msg):
#       print("DEvice Send", flush=True)
#       print(msg)
#       # self.pipe.send_multipart([b"COMMAND", msg])


#     # def ping(self, socket):
#     #     if time.time() > self.ping_at:
#     #         print("SEND PING FOR %s", self.identity)
#     #         socket.send_multipart([self.identity, b'PING', b'/'])
#     #         self.ping_at = time.time() + 1e-3*PING_INTERVAL
#     #     else:
#     #       print("NO PING: %s  ,  %s ", time.time(), self.ping_at)

#     # def tickless(self, tickless):
#     #     if tickless > self.ping_at:
#     #         tickless = self.ping_at
#     #     return tickless