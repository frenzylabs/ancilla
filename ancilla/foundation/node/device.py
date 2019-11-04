import threading
import time
import zmq
from zmq.eventloop.zmqstream import ZMQStream
import zmq.asyncio

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

    def __init__(self, ctx, name, **kwargs):    
        print(name, flush=True)  
        # query = Printer.select()
        # print(q)
        # query = Printer.select().where(Printer.name == name).limit(1)
        # self.record = query[0].json
        # for pr in query:
        #   print(pr.json)
        # print(type(query))
        # print(self.record)
        # self.endpoint = endpoint
        # if identity == None: 
        #   identity = endpoint
        self.identity = name
        # self.baudrate = baudrate
                
        # self.ping_at = time.time() + 1e-3*PING_INTERVAL
        # self.expires = time.time() + 1e-3*SERVER_TTL

        self.ctx = ctx #zmq.Context()
        
        self.pusher = self.ctx.socket(zmq.PUSH)
        self.pusher.connect(f"ipc://collector")

        collector = self.ctx.socket(zmq.PULL)
        collector.bind(f"inproc://{self.identity}_collector")

        # socket = self.ctx.socket(type)
        # socket.bind(endpoint)
        # self.voter_socket = socket
        # self.voter_callback = handler
        input_stream = self.ctx.socket(zmq.ROUTER)
        print(f"ipc://{self.identity.decode('utf-8')}_taskrouter")
        input_url = f"tcp://*:5558"
        input_stream.identity = b"printer"
        input_stream.bind(input_url)

        self.input_stream = ZMQStream(input_stream)
        self.input_stream.on_recv(self.on_message)
        self.input_stream.on_send(self.input_sent)
        self.data_stream = ZMQStream(collector)
        self.data_stream.on_recv(self.on_data)

    def register_data_handlers(self, obj):
      data_handlers.append(obj)

    def input_sent(self, msg, status):
      print("INPUT SENT", msg)

    def on_message(self, msg):
      print("ON MESSGE", msg)

    def on_data(self, data):
      print("ON DATA", data)
      self.pusher.send_multipart(data)

    def stop(self):
      print("stop")
    
    def start(self):
      print("RUN SERVER", flush=True)

    def send(self, msg):
      print(msg)
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