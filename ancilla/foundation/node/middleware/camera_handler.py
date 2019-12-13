from .data_handler import DataHandler
from ..events.camera import Camera
import json

class CameraHandler(DataHandler):
  def __init__(self, service, *args):
      self.service = service

  def handle(self, data):
      if not data or len(data) < 3:
        return

      identifier, frm_num, frame = data

      evt = "events." + Camera.data_received.value()
      return [evt.encode('ascii'), self.service.name.encode('ascii'), frm_num, frame]
      # return [b'events.camera.data_received', identifier, frm_num, frame]
      # super().on_data(data)
      # return data