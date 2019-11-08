import threading
import time
import zmq
import importlib
import json

from .device import Device
from ..data.models import Device

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

    def __init__(self, ctx, pipe, router):
        self.ctx = ctx
        self.pipe = pipe
        self.router = router
        self.device_models = {}
        for device in Device.select():
          identifier = device.name.encode('ascii')
          self.device_models[identifier] = device

        self.active_devices = {}

        self.check_devices()


        
    def __connect_device(self, identifier, model):
      try:
        DeviceCls = getattr(importlib.import_module("ancilla.foundation.node.devices"), model.device_type)
        device = DeviceCls(self.ctx, identifier)
        device.start()
        time.sleep(0.1) # Allow connection to come up
        # print("CONNECT DEVICE", flush=True)
        self.active_devices[identifier] = device
        return device
      except Exception as e:
          print(f"EXception connecting to device {str(e)}", flush=True)
          raise Exception(f'Could Not Connect to Device: {str(e)}')
          # self.pipe.send_multipart([identifier, b'Failed', f'Could Not Connect to Device: {str(e)}'.encode('ascii')])


    def __add_device(self, identifier, name, kind):
      try:
          model = Device.get(Device.name == name)
          self.device_models[identifier] = model
          return model

      except Exception as e:
          print(f"EXception adding device {str(e)}", flush=True)
          raise Exception(f'Device Does Not Exist: {str(e)}')
          # self.pipe.send_multipart([identifier, b'Failed', f'Device Does Not Exist: {str(e)}'.encode('ascii')])

    def check_devices(self):
      for (identifier, device_model) in self.device_models.items():
        try:
          
          print(device_model, flush=True)
          device = self.__connect_device(identifier, device_model)
          device.stop()
          
        except Exception as e:
          print(f"EXception connecting device: {str(e)}", flush=True)
          self.router.send_multipart([identifier, b'Failed', f'Printer Could Not Start: {str(e)}'.encode('ascii')])

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
            

            try:
              activedevice = self.active_devices.get(identity)
              if not activedevice:
                device_model = self.device_models.get(identity)
                if device_model:
                  activedevice = self.__connect_device(identity, device_model)
                else:
                  name = identity.decode('utf-8')
                  device_model = self.__add_device(identity, name, kind)
                  activedevice = self.__connect_device(identity, device_model)
  
              if activedevice:
                activedevice.connect()
                self.pipe.send_multipart([identity, b'Success', b'Device Connected'])
              else:
                self.pipe.send_multipart([identity, b'Failure', b'No Active Device'])

              # DeviceCls = getattr(importlib.import_module("ancilla.foundation.node.devices"), kind)

              # device = DeviceCls(self.ctx, identity)
              # device.start()
              # self.devices[identity] = device
              # self.actives.append(device)
              # self.pipe.send_multipart([identity, b'Success', b'Printer Started'])
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
            # assert not self.request    # Strict request-reply cycle
            # Prefix request with sequence number and empty envelope
            
            try:
              # identity = msg.pop(0)
              # action = msg.pop(0)
              identity, action, *other = msg

              activedevice = self.active_devices.get(identity)

              if activedevice:
                # [b'-1', action, *lparts = msg
                res = activedevice.send([b'-1', action, other])
                self.pipe.send_multipart([identity, b'resp', res.encode('ascii')])
              else:
                self.pipe.send_multipart([identity, b'resp', json.dumps({"error": 'Device Not Active'}).encode('ascii')])

              # DeviceCls = getattr(importlib.import_module("ancilla.foundation.node.devices"), kind)

              # device = DeviceCls(self.ctx, identity)
              # device.start()
              # self.devices[identity] = device
              # self.actives.append(device)
              # self.pipe.send_multipart([identity, b'Success', b'Printer Started'])
            except Exception as e:
              print(f"EXception connecting device {str(e)}")
              self.pipe.send_multipart([identity, b'Error', f'Could Not Make Request: {str(e)}'.encode('ascii')])


            # Request expires after global timeout
            # self.expires = time.time() + 1e-3*GLOBAL_TIMEOUT

    def router_message(self, router):

      msg = router.recv_multipart()
      print(f"Router Msg = {msg}", flush=True)
      
      node_identity, request_id, device_identity, action, *msgparts = msg
      print("Unpack here", flush=True)
      # msg = msg[2]
      # if len(msg) > 2:
      #   subtree = msg[2]
      message = ""
      if len(msgparts) > 0:
        message = msgparts[0]

      print("DEVICE IDENTITY here", flush=True)
      if device_identity:
        curdevice = self.active_devices.get(device_identity)
        if curdevice:
          res = curdevice.send([request_id, action, message])
          print(f"SEND RESPONSE = {res}", flush=True)
          resp = b''
          if res:
            resp = res.encode('ascii')
          router.send_multipart([node_identity, request_id, resp])
        else:
          
          msg = b'Device Does Not Exists'
          device_model = self.device_models.get(device_identity)
          if device_model:
            try:
              activedevice = self.__connect_device(device_identity, device_model)
              if activedevice:
                resp = b''
                if action == b'connect':
                  resp = b'Connected'
                else:
                  res = activedevice.send([request_id, action, message])                
                  if res:
                    resp = res.encode('ascii')

                router.send_multipart([node_identity, request_id, resp])
                return
            except:
              print("No active device", flush=True)
            msg = b'Device Is Not Active'
            
          print("Device doesn't exist", flush=True)
          router.send_multipart([node_identity, request_id, msg])
      else:
        print("NO router ", flush=True)
        router.send_multipart([node_identity, request_id, b'No Device'])

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
