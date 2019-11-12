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

        self.__check_devices()


        
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


    def __add_device(self, identifier, name):
      try:
          # identifier == bytes (since it's already in bytes format coming in we can leave it)
          model = Device.get(Device.name == name)
          self.device_models[identifier] = model
          return model

      except Exception as e:
          print(f"EXception adding device {str(e)}", flush=True)
          raise Exception(f'Device Does Not Exist: {str(e)}')
          # self.pipe.send_multipart([identifier, b'Failed', f'Device Does Not Exist: {str(e)}'.encode('ascii')])

    def __check_devices(self):
      for (identifier, device_model) in self.device_models.items():
        try:
          
          print(device_model, flush=True)
          device = self.__connect_device(identifier, device_model)
          device.stop()
          
        except Exception as e:
          print(f"EXception connecting device: {str(e)}", flush=True)
          self.router.send_multipart([identifier, b'Failed', f'Printer Could Not Start: {str(e)}'.encode('ascii')])

    def add_device(self, name):
      try:
        identifier = name.encode('ascii')
        model = self.__add_device(identifier, name)

        return [True, {"success": "Device Added"}]


      except Exception as e:
          print(f"EXception adding device {str(e)}", flush=True)
          return [False, {"error": "Could Not Add Device", "reason": str(e)}]
          # raise Exception(f'Device Does Not Exist: {str(e)}')

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
                  device_model = self.add_device(identity, name, kind)
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
          action, *payload = msg
      
          payload = {}
          
          try:
            if len(payload) > 0:
              payload = payload[0].decode('utf-8')
              payload = json.loads(payload)

            action_name = action.decode('utf-8').lower()
            method = getattr(self, action_name)
            isSuccessful = False
            msg = {'error': f'no action {action} found'}
            if method:
              [isSuccessful, msg] = method(**payload)  

            if isSuccessful:
              res = {"status": "ok"}
            # return json.dumps(res)
              self.pipe.send_multipart([b'success', json.dumps(msg).encode('ascii')])
            else:
              self.pipe.send_multipart([b'error', json.dumps(msg).encode('ascii')])

          except Exception as e:
            print(f'Send Exception: {str(e)}', flush=True)
            # return json.dumps({"error": str(e)})
            self.pipe.send_multipart([b'error', json.dumps({"error": str(e)}).encode('ascii')])

          

          

        elif command == b"DEVICE_REQUEST":
            # assert not self.request    # Strict request-reply cycle
            # Prefix request with sequence number and empty envelope
            print("INSIDE DEVICE_REQUEST")
            try:
              # identity = msg.pop(0)
              # action = msg.pop(0)
              identity, action, *other = msg
              response = {"action": action.decode('utf-8')}

              activedevice = self.active_devices.get(identity)

              if not activedevice:
                device_model = self.device_models.get(identity)
                if device_model:
                  activedevice = self.__connect_device(identity, device_model)
                else:
                  name = identity.decode('utf-8')
                  device_model = self.add_device(identity, name, kind)
                  activedevice = self.__connect_device(identity, device_model)
  
              if activedevice:
                res = activedevice.send([b'-1', action] + other)
                response.update({"resp": res})
                
                res = json.dumps(response)
                self.pipe.send_multipart([identity, b'success', res.encode('ascii')])
              else:
                response.update({"resp": {"error": 'Device Not Active'}})
                self.pipe.send_multipart([identity, b'error', json.dumps(response).encode('ascii')])

              # if activedevice:
              #   # [b'-1', action, *lparts = msg
              #   res = activedevice.send([b'-1', action, other])
              #   # if type(res) == dict:
              #   #   response.update({"resp"})
                
              #   response.update({"resp": res})
                
              #   res = json.dumps(response)
              #   self.pipe.send_multipart([identity, b'success', res.encode('ascii')])
              # else:
              #   response.update({"resp": {"error": 'Device Not Active'}})
              #   self.pipe.send_multipart([identity, b'error', json.dumps(response).encode('ascii')])


            except Exception as e:
              print(f"EXception connecting device {str(e)}")
              self.pipe.send_multipart([identity, b'error', json.dumps({"error": 'Could Not Make Request', "reason": str(e)}).encode('ascii')])


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
      response = {"request_id": request_id.decode('utf-8'), "action": action.decode('utf-8')}

      if device_identity:
        curdevice = self.active_devices.get(device_identity)
        if curdevice:
          res = curdevice.send([request_id, action, message])
          print(f"SEND RESPONSE = {res}", flush=True)
          
          if res:
            response.update({"resp": res})
            # res = {}
          # resp = json.dumps(res.encode('ascii'))
          # router.send_multipart([node_identity, device_identity, resp])
        else:
          

          # msg = b'Device Does Not Exists'
          # msg = {"status": "error","reason": "Device Does Not Exists"}
          # msg = b'{"status": "error","reason": "Device Does Not Exists"}'
          device_model = self.device_models.get(device_identity)
          if not device_model:
            response.update({"resp": {"status": "error","reason": "Device Does Not Exists"}})
          else:
            try:
              print(device_model, flush=True)
              activedevice = self.__connect_device(device_identity, device_model)
              print("CONNECT TO ACTIVE DEVICE")
              if activedevice:
                resp = b''
                if action == b'connect':
                  resp = b'Connected'
                  response.update({"resp": {"status": "Connected"}})
                else:
                  res = activedevice.send([request_id, action, message])                
                  if res:
                    response.update({"resp": res})
                    # resp = res.encode('ascii')

                # router.send_multipart([node_identity, device_identity, resp])
                # return
            except:
              print("No active device", flush=True)
              # msg = b'{"status": "error","reason": "Device Is Not Active"}'
              msg = {"status": "error","reason": "Device Is Not Active"}
              response.update({"resp": msg})
          
            
          # print("Device doesn't exist", flush=True)
          # router.send_multipart([node_identity, device_identity, msg])
      else:
        print("NO router ", flush=True)
        response.update({"resp": {"status": "error","reason": "No Device"}})
        # router.send_multipart([node_identity, device_identity, b'No Device'])

      router.send_multipart([node_identity, device_identity, json.dumps(response).encode('ascii')])

      

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
