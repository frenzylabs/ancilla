import threading
import time
import zmq
from tornado.ioloop import IOLoop

from .zhelpers import zpipe
from .agent    import NodeAgent
from ..data.models import Device, DeviceRequest

class NodeServer(object):
    ctx = None      # Our Context
    pipe = None     # Pipe through to flciapi agent
    agent = None    # agent in a thread
    identity = b'localhost'
    servers = {}

    def __init__(self, identity=b'localhost'):
        self.identity = identity
        self.ctx = zmq.Context()
        self.pipe, peer = zpipe(self.ctx)        

        self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer))
        self.agent.daemon = True
        self.agent.start()


    def connect(self, endpoint, identity = None):
        """Connect to new server endpoint
        Sends [CONNECT][endpoint] to the agent
        """
        if identity == None: 
          identity = endpoint
        print("identity = ", identity)
        self.pipe.send_multipart([b"CONNECT", endpoint.encode('ascii'), identity.encode('ascii')])
        time.sleep(0.1) # Allow connection to come up

    def add_device(self, kind, endpoint, identity = None):
        if identity == None: 
          identity = endpoint
        print("identity = ", identity)
        self.pipe.send_multipart([b"CONNECT_DEVICE", kind.encode('ascii'), endpoint.encode('ascii'), identity.encode('ascii')])
        reply = self.pipe.recv_multipart()
        # time.sleep(0.1) # Allow connection to come up
        name, status, msg = reply
        return {"name": name.decode('utf-8'), "status": status.decode('utf-8'), "msg": msg.decode('utf-8')}
        # return reply

    def add_client(self, endpoint, identity = None):
        """Connect to new server endpoint
        Sends [CONNECT][endpoint] to the agent
        """
        if identity == None: 
          identity = endpoint
        print("identity = ", identity)
        self.pipe.send_multipart([b"CONNECT_LOCAL_PRINTER", endpoint.encode('ascii'), identity.encode('ascii')])
        time.sleep(0.1) # Allow connection to come up        

    def request(self, msg):
        # print("Send request, get reply")
        request = [b"REQUEST"] + msg
        self.pipe.send_multipart(request)
        reply = self.pipe.recv_multipart()
        status = reply.pop(0)
        if status != "FAILED":
            return reply


    def run_server(self, ctx, pipe):
        print("INSIDE AGENT TASK", flush=True)
        loop = IOLoop().initialize()  
        loop = IOLoop.current()
        agent = NodeAgent(ctx, pipe)

        router = ctx.socket(zmq.ROUTER)
        router.identity = self.identity
        router.bind("tcp://*:5556")

        publisher = ctx.socket(zmq.PUB)
        publisher.bind("ipc://publisher")
        # publisher.bind("ipc://publisher")
        # publisher.bind("tcp://*:5557")
        collector = ctx.socket(zmq.PULL)
        collector.bind("ipc://collector")
        # collector.bind("tcp://*:5558")

        sequence = 0
        kvmap = {}

        poller = zmq.Poller()
        poller.register(collector, zmq.POLLIN)
        poller.register(router, zmq.POLLIN)
        poller.register(agent.pipe, zmq.POLLIN)
        # poller.register(agent.router, zmq.POLLIN)
        while True:
            try:
                items = dict(poller.poll(2000))
            except:
                break           # Interrupted

            if agent.pipe in items:
                agent.control_message()

            # if agent.router in items:
            #     agent.router_message()

            # print("INSIDE AGENT tASK")
            # If we're processing a request, dispatch to next server
            # if (agent.request):
            #     print("Agent Request", flush=True)
            #     if (time.time() >= agent.expires):
            #         # Request expired, kill it
            #         agent.pipe.send(b"FAILED")
            #         agent.request = None
            #     else:
            #         # Find server to talk to, remove any expired ones
            #         while agent.actives:
            #             server = agent.actives[0]
            #             if time.time() >= server.expires:
            #                 server.alive = 0
            #                 agent.actives.pop(0)
            #             else:
            #                 print("agent router request")
            #                 request = [server.identity] + agent.request
            #                 agent.router.send_multipart(request)
            #                 break

            # print("GET ITEMS", flush=True)
            # Apply state update sent from devices
            if collector in items:
                # print("INSIDE SERVER COLLECTOR", flush=True)
                msg = collector.recv_multipart()
                publisher.send_multipart(msg)

            # Execute state snapshot request
            if router in items:
                print("RECEIVED ITEM in server", flush=True)
                agent.router_message(router)
                
                # msg = router.recv_multipart()
                # print(msg)
                # device_identity = None
                # node_identity, request_id, device_identity, action, *msgparts = msg

                # if len(msgparts)
                # # node_identity = msg.pop(0)
                # # request_id = msg.pop(0)
                # # if len(msg) > 2:
                # #   device_identity = msg.pop(0)
                
                # # action = msg.pop(0)
                # # message = msg.pop(0)
                # # print("router item", device_identity)
                # # msg = msg[2]
                # # if len(msg) > 2:
                # #   subtree = msg[2]
                # if device_identity:
                #   curdevice = agent.devices.get(device_identity)
                #   if curdevice:
                #     res = curdevice.send([action, message])
                #     if res:
                #       router.send_multipart([node_identity, res.encode('ascii')])
                #   else:
                #     print("Device doesn't exist")
                #     router.send_multipart([node_identity, b'Device Does Not Exists'])
                # else:
                #   print(agent.devices)
                  
                #   server = None
                #   for key, val in agent.servers.items():    # for name, age in dictionary.iteritems():  (for Python 2.x)
                #     if val.identity == identity:
                #       server = val

                
                # # server = agent.servers[identity]
                # if server:
                #   server.send(msg)