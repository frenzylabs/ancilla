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
import importlib
# from ..zhelpers import zpipe

# import cv2

import os
import shutil

import json


# from ..zhelpers import zpipe, socket_set_hwm
from ....data.models import Camera as CameraModel, CameraRecording
# from ...base_service import BaseService
# from ....utils.service_json_encoder import ServiceJsonEncoder

# from ...data.models import DeviceRequest

# from queue import Queue
# import asyncio

# from tornado.queues     import Queue
# from tornado import gen
# from tornado.gen        import coroutine, sleep
from collections import OrderedDict
# import struct # for packing integers
# from zmq.eventloop.ioloop import PeriodicCallback

# from zmq.asyncio import Context, ZMQEventLoop

# from zmq.eventloop.zmqstream import ZMQStream
# from tornado.ioloop import IOLoop, PeriodicCallback



# from ....data.models import Printer as PrinterModel
# from ...base_service import BaseService
# from .driver import SerialConnector

# from ....data.models import PrinterCommand, PrintSlice, Print
# from queue import Queue

# from tornado.queues     import Queue
# from tornado import gen
# from tornado.gen        import coroutine, sleep
# from collections import OrderedDict
# import struct # for packing integers
# from zmq.eventloop.ioloop import PeriodicCallback


# from ...tasks.ancilla_task import PeriodicTask
# from ...tasks.print_task import PrintTask




# from ..tasks.device_task import PeriodicTask


# from ...events import Event, EventPack, Service as EventService
# from ...events.printer import Printer as PrinterEvent
# from ...events.event_pack import EventPack
# from ...middleware.printer_handler import PrinterHandler as PrinterDataHandler
# from ...response import AncillaResponse, AncillaError
# from ...request import Request



class CommandQueue(object):

    def __init__(self):
        self.queue = OrderedDict()
        self.current_command = None
        self.current_expiry = None
        self.callbacks = OrderedDict()

    def add(self, cmd, cb = None):
        self.queue.pop(cmd.identifier(), None)
        self.queue[cmd.identifier()] = cmd
        self.callbacks[cmd.identifier()] = cb

    def get_command(self):
      if not self.current_command and len(self.queue) > 0:
        cid, cmd = self.queue.popitem(False)
        self.current_command = cmd
        self.current_expiry = time.time() + 5000
      return self.current_command 

    def finish_command(self, status="finished"):
      # print("FINISH Cmd", flush=True)
      if self.current_command:
        self.current_command.status = status
        # cb = self.callbacks[self.current_command.identifier()]
        cb = self.callbacks.pop(self.current_command.identifier(), None)
        if cb:
          res = cb(self.current_command.__data__)
          
        # self.current_command.save()
      self.current_command = None
      self.current_expiry = None

    def update_expiry(self):
        self.current_expiry = time.time() + 5000

    def clear(self):
      self.queue.clear()
      self.current_command = None
      self.current_expiry = None

    def __next__(self):
        address, worker = self.queue.popitem(False)
        return address
    
