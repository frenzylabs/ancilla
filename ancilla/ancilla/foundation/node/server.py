# import threading
# import time
# import zmq
# from tornado.ioloop import IOLoop

# from .zhelpers import zpipe
# from .agent    import NodeAgent
# from ..data.models import Device, DeviceRequest

# class NodeServer(object):
#     ctx = None      # Our Context
#     pipe = None     # Pipe through to flciapi agent
#     agent = None    # agent in a thread
#     identity = b'localhost'
#     servers = {}

#     def __init__(self, identity=b'localhost'):
#         self.identity = identity
#         self.name = identity.decode('utf-8')
#         self.ctx = zmq.Context()
#         self.pipe, peer = zpipe(self.ctx)        

#         self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer))
#         self.agent.daemon = True
#         self.agent.name = f"Node{self.name}"
#         self.agent.start()
#         time.sleep(0.5) # Allow connection to come up

#         def __init__(self, ctx, name, **kwargs):    
#         print(f'DEVICE NAME = {name}', flush=True)  
#         if type(name) == bytes:
#           self.identity = name
#           self.name = name.decode('utf-8')
#         else:
#           self.name = name
#           self.identity = name.encode('ascii')
#         self.data_handlers = []
#         self.task_queue = Queue()
#         self.current_task = {}
#         self.state = {}
#         self.events = []
#         # self.ping_at = time.time() + 1e-3*PING_INTERVAL
#         # self.expires = time.time() + 1e-3*SERVER_TTL

#         zmq.Context()
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

#         self.event_stream = self.ctx.socket(zmq.SUB)
#         self.event_stream.connect("ipc://publisher")
#         self.event_stream = ZMQStream(self.event_stream)
#         self.event_stream.on_recv(self.on_message)


#     def add_device(self, kind, endpoint, identity = None):
#         if identity == None: 
#           identity = endpoint
#         # print("identity = ", identity)
#         self.pipe.send_multipart([b"CONNECT_DEVICE", kind.encode('ascii'), endpoint.encode('ascii'), identity.encode('ascii')])
#         reply = self.pipe.recv_multipart()
#         # print("ADD DEVICE REPLY", reply)
#         # time.sleep(0.1) # Allow connection to come up
#         name, status, msg = reply
#         return {"name": name.decode('utf-8'), "status": status.decode('utf-8'), "msg": msg.decode('utf-8')}
#         # return reply

#     # def add_client(self, endpoint, identity = None):
#     #     """Connect to new server endpoint
#     #     Sends [CONNECT][endpoint] to the agent
#     #     """
#     #     if identity == None: 
#     #       identity = endpoint
#     #     print("identity = ", identity)
#     #     self.pipe.send_multipart([b"CONNECT_LOCAL_PRINTER", endpoint.encode('ascii'), identity.encode('ascii')])
#     #     time.sleep(0.1) # Allow connection to come up        

#     def device_request(self, msg):
#         # print("Send request, get reply")
#         request = [b"DEVICE_REQUEST"] + msg
#         self.pipe.send_multipart(request)
#         reply = self.pipe.recv_multipart()
#         ident, status, msg = reply
#         # return [status.decode('utf-8'), msg.decode('utf-8')]
#         return msg.decode('utf-8')

#     def request(self, msg):
#         # print("Send request, get reply")
#         request = [b"REQUEST"] + msg
#         self.pipe.send_multipart(request)
#         reply = self.pipe.recv_multipart()
#         status, msg = reply
#         return msg.decode('utf-8')
#         # return [status.decode('utf-8'), msg.decode('utf-8')]
#         # return reply
#         # status = reply.pop(0)
#         # if status != "FAILED":
#         #     return reply


#     def run_server(self, ctx, pipe):
#         print("INSIDE AGENT TASK", flush=True)
#         loop = IOLoop().initialize(make_current=True)  
#         # loop = IOLoop.current(instance=True)

#         router = ctx.socket(zmq.ROUTER)
#         router.identity = self.identity
#         router.bind("tcp://*:5556")
#         time.sleep(0.5)

#         agent = NodeAgent(ctx, pipe, router)

#         # print("NODE_SERVER before publisher bind", flush=True)
#         publisher = ctx.socket(zmq.PUB)
#         publisher.bind("ipc://publisher")
#         # publisher.bind("tcp://*:5557")

#         # eventsubscriber = ctx.socket(zmq.SUB)
#         # eventsubscriber.bind("ipc://subscriber")

#         # print("NODE_SERVER before collector bind", flush=True)
#         collector = ctx.socket(zmq.PULL)
#         collector.bind("ipc://collector")
#         # collector.bind("tcp://*:5558")

#         sequence = 0
#         kvmap = {}

#         poller = zmq.Poller()
#         poller.register(collector, zmq.POLLIN)
#         poller.register(router, zmq.POLLIN)
#         poller.register(agent.pipe, zmq.POLLIN)
#         # poller.register(agent.router, zmq.POLLIN)
#         print("INSIDE NODE SERVER", flush=True)
        
#         while True:
#             try:
#                 items = dict(poller.poll(1000))
#             except:
#                 break           # Interrupted4

#             if agent.pipe in items:
#                 # print("INSIDE AGENT PIPE", flush=True)
#                 agent.control_message()


#             # print("GET ITEMS", flush=True)
#             # Apply state update sent from devices
#             if collector in items:
                
#                 msg = collector.recv_multipart()
#                 publisher.send_multipart(msg)
#                 if len(msg) >= 3:
#                     topic, device, *other = msg
#                     # topic, device, payload, *other = msg
#                     if topic.startswith(b'events.'):
#                         publisher.send_multipart([device + b'.' + topic, device] + other)
#                         # publisher.send_multipart([device + b'.' + topic, device, payload])
                    
                    
#                 # print(f"INSIDE SERVER COLLECTOR {msg}", flush=True)
#                 # publisher.send_multipart(msg)

#             # Execute state snapshot request
#             if router in items:
#                 # print("RECEIVED ITEM in server", flush=True)
#                 agent.router_message(router)

#         # print("OUTSIDE NODE WHILE LOOP", flush=True)
#         router.close()
#         publisher.close()
#         collector.close()
#         ctx.term()