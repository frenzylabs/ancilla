import threading
import time
import sys
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio

from tornado.queues import Queue
from tornado.ioloop import IOLoop
from .zhelpers import zpipe
from ..data.models import Printer
# from .devices import *

class Device(object):
    endpoint = None         # Server identity/endpoint
    identity = None
    alive = True            # 1 if known to be alive
    ping_at = 0             # Next ping at this time
    expires = 0             # Expires at this time
    workers = []
    data_handlers = []
    request_handlers = []
    interceptors = []
    data_stream = None
    input_stream = None
    pusher = None
    task_queue = Queue()
    

    def __init__(self, ctx, name, **kwargs):    
        print(f'DEVICE NAME = {name}', flush=True)  
        self.identity = name
        # self.ping_at = time.time() + 1e-3*PING_INTERVAL
        # self.expires = time.time() + 1e-3*SERVER_TTL

        self.ctx = ctx #zmq.Context()

        self.pusher = self.ctx.socket(zmq.PUSH)
        self.pusher.connect(f"ipc://collector")

        # self.ctx = zmq.Context()
        deid = f"inproc://{self.identity}_collector"
        self.data_stream = self.ctx.socket(zmq.PULL)
        # print(f'BEFORE CONNECT COLLECTOR NAME = {deid}', flush=True)  
        self.data_stream.bind(deid)
        time.sleep(0.1)        
        self.data_stream = ZMQStream(self.data_stream)
        # self.data_stream.stop_on_recv()

        self.input_stream = self.ctx.socket(zmq.ROUTER)
        # print(f"ipc://{self.identity.decode('utf-8')}_taskrouter", flush=True)
        input_url = f"ipc://{self.identity.decode('utf-8')}_taskrouter"
        # input_url = f"tcp://*:5558"
        self.input_stream.identity = f"{self.identity.decode('utf-8')}_input".encode('ascii')  #self.identity #b"printer"
        self.input_stream.bind(input_url)
        time.sleep(0.1)

        self.input_stream = ZMQStream(self.input_stream)
        # self.input_stream.on_recv(self.on_message)
        # self.input_stream.on_send(self.input_sent)
        IOLoop.current().add_callback(self.start_receiving)
        # sys.stderr.flush()


    def start_receiving(self):
      # print("Start receiving", flush=True)
      self.data_stream.on_recv(self.on_data)
      # self.input_stream.on_recv(self.on_message)

    def register_data_handlers(self, obj):
      self.data_handlers.append(obj)

    def input_sent(self, msg, status):
      print("INPUT SENT", msg)

    def on_message(self, msg):
      print("ON MESSGE", msg)

    def on_tada(self, *args):
      print("ON TADA", flush=True)

    def on_data(self, data):
      # print("ON DATA", data)
      for d in self.data_handlers:
        data = d.handle(data)

      self.pusher.send_multipart(data)

    def stop(self):
      print("stop")
    
    def start(self):
      print("RUN SERVER", flush=True)

    def send(self, msg):
      print("DEvice Send", flush=True)
      print(msg)
  

    # async def _process_tasks(self):
    # # print("About to get queue", flush=True)
    #   async for item in self.task_queue:
    #   # print('consuming {}...'.format(item))
    #     (method, request_id, msg) = item
    #     await method(request_id, msg)


    # async def _add_task(self, msg):
    #   await self.task_queue.put(msg)


    # def start_print(self, request_id, data):
    #   request = DeviceRequest.get_by_id(request_id)
    #   if self.print_queued:
    #     request.status = "unschedulable"
    #     request.save()
    #     self.publish_request(request)
    #     return {"error": "Printer Busy"}
      
    #   loop = IOLoop().current()
      
    #   self.task_queue.put((self.print_task, request_id, data))
    #   self.print_queued = True
    #   loop.add_callback(partial(self._process_tasks))
    #   self.task_queue.join()

    #   return {"queued": "success"}

      # self.pipe.send_multipart([b"COMMAND", msg])


    # def ping(self, socket):
    #     if time.time() > self.ping_at:
    #         print("SEND PING FOR %s", self.identity)
    #         socket.send_multipart([self.identity, b'PING', b'/'])
    #         self.ping_at = time.time() + 1e-3*PING_INTERVAL
    #     else:
    #       print("NO PING: %s  ,  %s ", time.time(), self.ping_at)

    # def tickless(self, tickless):
    #     if tickless > self.ping_at:
    #         tickless = self.ping_at
    #     return tickless