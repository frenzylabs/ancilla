import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
from ..zhelpers import zpipe

import cv2

class CameraConnector(object):
  def __init__(self, ident, pub_endpoint, endpoint, baudrate, pipe, debug = True):
    self.publisher_endpoint = pub_endpoint
    self.identity = ident
    self.serial_endpoint = endpoint

    ctx = zmq.Context.instance()   
    socket = ctx.socket(zmq.PUB)
    socket.bind(f'ipc://{self.identity}')

    capture = cv2.VideoCapture('rtsp://192.168.1.64/1')
    # socket.bind("tcp://*:5555")
    self.video = cv2.VideoCapture(0)



# class CameraDevice(object):
#     endpoint = None         # Server identity/endpoint
#     identity = None
#     alive = True            # 1 if known to be alive
#     ping_at = 0             # Next ping at this time
#     expires = 0             # Expires at this time

#     def __init__(self, endpoint, identity = None):      
#         self.endpoint = endpoint
#         if identity == None: 
#           identity = endpoint
#         self.identity = identity

#         self.alive = True        
#         self.ping_at = time.time() + 1e-3*PING_INTERVAL
#         self.expires = time.time() + 1e-3*SERVER_TTL

#         self.ctx = zmq.Context()
#         self.pipe, peer = zpipe(self.ctx)        
#         # self.server = threading.Thread(target=run_server, args=(self.ctx,))
#         # self.server.daemon = True
#         # self.server.start()
#         self.agent = threading.Thread(target=self.run_server, args=(self.ctx,peer,))
#         self.agent.daemon = True
#         self.agent.start()

#     def run_server(self, ctx, pipe):
#       print("RUN Camera SERVER", flush=True)
#       publisher = ctx.socket(zmq.PUB)
#       publisher.bind(f'ipc://devicepublisher')
#       # publisher.connect("ipc://collector")
#       # publisher.send_multipart([b'ender3', b'hello there'])
#       # if self.endpoint
#       # 'rtsp://192.168.1.64/1'
#       endpoint = self.endpoint.decode('utf-8')
#       if endpoint == '0':
#         endpoint = 0
#       video = cv2.VideoCapture(endpoint)
#       # camera = CameraConn(self.identity, "ipc://collector", self.endpoint.decode("utf-8"), self.baudrate, pipe)
#       i=0
#       # topic = 'camera_frame'
#       while self.alive:
#           i += 1
#           ret, frame = video.read()
#           # frame = video.read()
#           print("HI", ret)

#           # publisher.send_multipart([self.identity, frame])
#           publisher.send(self.identity, zmq.SNDMORE)
#           publisher.send(f'{i}'.encode('ascii'), zmq.SNDMORE)
#           publisher.send_pyobj(frame)
#           # time.sleep(2)
#           print('Sent frame {}'.format(i))

#       # while self.alive:
#       #   try:
#       #       cmd, data = pipe.recv_multipart()
#       #       print("Received Data: ", data)
#       #       if data:
#       #         serial_conn.serial.write(data+b'\n')
#       #   except Exception as msg:
#       #       print('{}'.format(msg))            
#       #       # probably got disconnected
#       #       break


#     def send(self, msg):
#       print(msg)    