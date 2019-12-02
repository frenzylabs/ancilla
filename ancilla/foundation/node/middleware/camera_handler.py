from .data_handler import DataHandler
import json

class CameraHandler(DataHandler):
  def __init__(self, device, *args):
      self.device = device

  def handle(self, data):
      if not data or len(data) < 3:
        return

      identifier, frm_num, frame = data

      return [b'events.camera.data_received', identifier, frm_num, frame]
      # super().on_data(data)
      # return data