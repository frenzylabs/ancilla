'''
 camera.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''


import logging
import socket
import sys
import time
import threading
import serial
import serial.rfc2217
import zmq
# from ..zhelpers import zpipe

# import cv2

import threading
import time
import zmq
import os
import shutil

import json
from tornado.ioloop import IOLoop

# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
from ...base_service import BaseService
from ....utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest
from .driver import CameraConnector
# from queue import Queue
# import asyncio
from functools import partial
from tornado.queues     import Queue
from tornado import gen
from tornado.gen        import coroutine, sleep
from collections import OrderedDict
import struct # for packing integers
from zmq.eventloop.ioloop import PeriodicCallback
import string, random



from ...tasks.camera_record_task import CameraRecordTask
from ...tasks.camera_process_video_task import CameraProcessVideoTask

from ...events.camera import Camera as CameraEvent
from ...events.event_pack import EventPack
from ...middleware.camera_handler import CameraHandler
from ...api.camera import CameraApi
from ...response import AncillaResponse, AncillaError


from multiprocessing import Process, Lock, Pipe
import multiprocessing as mp

class RemoteService():
    # connector = None
    # endpoint = None         # Server identity/endpoint
    # identity = None
    # alive = True            # 1 if known to be alive
    # ping_at = 0             # Next ping at this time
    # expires = 0             # Expires at this time
    # state = "IDLE"
    # recording = False
    
    # command_queue = CommandQueue()
    __actions__ = [
      "start_recording",
      "stop_recording",
      "resume_recording",
      "pause_recording",
      "print_state_change"
    ]

    def __init__(self, identity, conn, **kwargs):        
        super().__init__(**kwargs)
        self.identity = identity
        self.conn = conn
        self.loop = IOLoop().initialize(make_current=True)  
        self.ctx = zmq.Context.instance()
        # self.camera_handler = CameraHandler(self)
        # self.register_data_handlers(self.camera_handler)
        # self.api = CameraApi(self)
        # self.connector = None
        # self.video_processor = None

        # self.event_class = CameraEvent

        # self.state.load_dict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "recording": False
        # })

        # self.register_data_handlers(PrinterHandler(self))

    # def actions(self):
    #   return [
    #     "record"
    #   ]

    def run(self):
        print("INSIDE AGENT TASK", flush=True)
        
        # loop = IOLoop.current(instance=True)

        
        self.bind_address = "tcp://*:5556"
        self.router_address = "tcp://127.0.0.1:5556"

        zrouter = self.ctx.socket(zmq.ROUTER)
        zrouter.identity = self.identity
        zrouter.bind(self.bind_address)
        self.zmq_router = ZMQStream(zrouter, IOLoop.current())
        self.zmq_router.on_recv(self.router_message)
        self.zmq_router.on_send(self.router_message_sent)

        
    def router_message_sent(self, msg, status):
      print("INSIDE ROUTE SEND", flush=True)

    def router_message(self, msg):
      print("INSIDE ROUTE message", flush=True)
