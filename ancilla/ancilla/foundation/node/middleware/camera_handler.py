'''
 camera_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .data_handler import DataHandler
from ..events.camera import Camera
import json

class CameraHandler(DataHandler):
  def __init__(self, service, *args):
      super().__init__(service, *args)


  def handle(self, data):
      if not data or len(data) < 3:
        return

      fromidentifier, frm_num, msg = data

      identifier, *rest = fromidentifier.split(b'.')

      if len(rest) > 0:
        eventkind = b'.'.join(rest)
      else:
        eventkind = b'data_received'

      if eventkind == b'connection.closed' or frm_num == b'error':
        decodedmsg = msg.decode('utf-8')
        if frm_num == b'error':          
          self.logger.error(f"Camera Error: {decodedmsg}")
        else:
          self.logger.info(f"Camera Connection Closed: {decodedmsg}")
        self.service.state.connected = False
        self.service.fire_event(Camera.connection.closed, self.service.state)
        eventkind = b'events.camera.' + eventkind
      else:
        eventkind = b'data.camera.' + eventkind


      return [eventkind, identifier, frm_num, msg]
