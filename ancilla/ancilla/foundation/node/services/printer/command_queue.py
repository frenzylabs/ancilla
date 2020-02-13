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

from collections import OrderedDict


class CommandQueue(object):

    def __init__(self):
        self.max_send_queue_length = 10
        self.queue = OrderedDict()
        self.current_command = None
        self.current_expiry = None
        self.callbacks = OrderedDict()
        self.current_commands = OrderedDict()

    def add(self, cmd, cb = None):
        self.queue.pop(cmd.identifier(), None)
        self.queue[cmd.identifier()] = cmd
        self.callbacks[cmd.identifier()] = cb

    # def get_command(self):
    #   if not self.current_command and len(self.queue) > 0:
    #     cid, cmd = self.queue.popitem(False)
    #     self.current_command = cmd
    #     self.current_expiry = time.time() + 5000
    #   return self.current_command

    def get_next_command(self):
      if len(self.queue) > 0 and len(self.current_commands) < self.max_send_queue_length:
        cid, cmd = self.queue.popitem(False)
        self.current_commands[cid] = cmd
      return cmd

    def get_active_command(self):
      if not self.current_command and len(self.current_commands) > 0:
        cid, cmd = self.current_commands.popitem(False)
        self.current_command = cmd
        self.current_expiry = time.time() + 5000
      return self.current_command

    def finish_command(self, cmd, status="finished"):
      cmd.status = status
      cb = self.callbacks.pop(cmd.identifier(), None)
      if cb:
          res = cb(cmd.__data__)
      self.current_commands.pop(cmd.identifier(), None)
      


    def finish_current_command(self, status="finished"):
      # print("FINISH Cmd", flush=True)
      if self.current_command:
        self.finish_command(self.current_command, status=status)
        # self.current_command.status = status
        # # cb = self.callbacks[self.current_command.identifier()]
        # cb = self.callbacks.pop(self.current_command.identifier(), None)
        # if cb:
        #   res = cb(self.current_command.__data__)
          
        # self.current_command.save()
      self.current_command = None
      self.current_expiry = None

    def update_expiry(self):
        self.current_expiry = time.time() + 5000

    def clear(self):
      self.queue.clear()
      self.current_commands.clear()
      self.callbacks.clear()
      self.current_command = None
      self.current_expiry = None

    def __next__(self):
        address, worker = self.queue.popitem(False)
        return address
    
