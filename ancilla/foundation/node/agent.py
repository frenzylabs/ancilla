import threading
import time
import zmq
import importlib
import json

from .device import Device

class NodeAgent(object):
    ctx = None              # Own context
    pipe = None             # Socket to talk back to application
    router = None           # Socket to talk to servers
    devices = None          # Servers we've connected to
    actives = None          # Servers we know are alive
    sequence = 0            # Number of requests ever sent
    request = None          # Current request if any
    reply = None            # Current reply if any
    expires = 0             # Timeout for request/reply

    def __init__(self, ctx, pipe):
        self.ctx = ctx
        self.pipe = pipe
        self.router = ctx.socket(zmq.ROUTER)
        self.devices = {}
        self.actives = []

    def control_message (self):
        msg = self.pipe.recv_multipart()
        print("CONTROL MSG = ", msg)
        command = msg.pop(0)
        if command == b"CONNECT_DEVICE":
            kind = msg.pop(0).decode('utf-8')
            endpoint = msg.pop(0)
            # if len(msg) > 0:
            identity = msg.pop(0)
            print("I: connecting to %s...\n" % identity)
            # self.router.connect(endpoint)
            if self.devices.get(identity):
              self.pipe.send_multipart([identity, b'Success', b'Printer Exist'])
            else:
              try:
                DeviceCls = getattr(importlib.import_module("ancilla.foundation.node.devices"), kind)

                device = DeviceCls(self.ctx, identity)
                device.start()
                self.devices[identity] = device
                self.actives.append(device)
                self.pipe.send_multipart([identity, b'Success', b'Printer Started'])
              except Exception as e:
                print(f"EXception connecting device {str(e)}")
                self.pipe.send_multipart([identity, b'Failed', f'Printer Could Not Start: {str(e)}'.encode('ascii')])

            # these are in the C case, but seem redundant:
            # server.ping_at = time.time() + 1e-3*PING_INTERVAL
            # server.expires = time.time() + 1e-3*SERVER_TTL
        # elif command == b"CONNECT":
        #     endpoint = msg.pop(0)
        #     # if len(msg) > 0:
        #     identity = msg.pop(0)
        #     print("I: connecting to %s...\n" % endpoint)
        #     self.router.connect(endpoint)
            
        #     server = FreelanceServer(endpoint, identity)
        #     print(server)
        #     self.servers[endpoint] = server
        #     self.actives.append(server)
        #     # these are in the C case, but seem redundant:
        #     server.ping_at = time.time() + 1e-3*PING_INTERVAL
        #     server.expires = time.time() + 1e-3*SERVER_TTL
        elif command == b"REQUEST":
            assert not self.request    # Strict request-reply cycle
            # Prefix request with sequence number and empty envelope
            self.request = [str(self.sequence).encode('ascii'), b''] + msg

            # Request expires after global timeout
            # self.expires = time.time() + 1e-3*GLOBAL_TIMEOUT

    def router_message(self, router):
      msg = router.recv_multipart()
      print("Router Msg = ", msg)
      node_identity, request_id, device_identity, action, *msgparts = msg
      # msg = msg[2]
      # if len(msg) > 2:
      #   subtree = msg[2]
      message = ""
      if len(msgparts) > 0:
        message = msgparts[0]

      if device_identity:
        curdevice = self.devices.get(device_identity)
        if curdevice:
          res = curdevice.send([request_id, action, message])
          if res:
            router.send_multipart([node_identity, request_id, res.encode('ascii')])
        else:
          print("Device doesn't exist")
          router.send_multipart([node_identity, request_id, b'Device Does Not Exists'])
      else:
        print(agent.devices)

    # def router_message (self):
    #     reply = self.router.recv_multipart()
    #     print("router messages", flush=True)
    #     # Frame 0 is server that replied
    #     identity = reply.pop(0)
    #     device = self.devices[identity]
    #     if not device.alive:
    #         self.devices.append(device)
    #         device.alive = 1

    #     # server.ping_at = time.time() + 1e-3*PING_INTERVAL
    #     # server.expires = time.time() + 1e-3*SERVER_TTL;

    #     # Frame 1 may be sequence number for reply
    #     # sequence = reply.pop(0)
    #     # if int(sequence) == self.sequence:
    #     #     self.sequence += 1
    #     reply = [b"OK"] + reply
    #     self.pipe.send_multipart(reply)
    #     self.request = None    
