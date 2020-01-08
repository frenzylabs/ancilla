from .data_handler import DataHandler
from ..events.camera import Camera
import json

class CameraHandler(DataHandler):
  def __init__(self, service, *args):
      self.service = service

  def handle(self, data):
      if not data or len(data) < 3:
        return

      fromidentifier, frm_num, msg = data

      identifier, *rest = fromidentifier.split(b'.')

      if len(rest) > 0:
        eventkind = b'.'.join(rest)
      else:
        eventkind = b'data_received'

      if eventkind == b'connection.closed':
        self.service.state.connected = False
        self.service.fire_event(Camera.connection.closed, self.service.state)

      # identifier, frm_num, frame = data

      return [b'events.camera.' + eventkind, identifier, frm_num, msg]
