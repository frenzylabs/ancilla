from ....middleware.data_handler import DataHandler

from ..events import Camera


class CameraHandler(DataHandler):
  def __init__(self, device, *args):
      self.device = device

  def handle(self, data):
      if not data or len(data) < 3:
        return

      identifier, frm_num, frame = data

      evt = "events." + Camera.data_received.value()
      return [evt.encode('ascii'), identifier, frm_num, frame]
      # return [b'events.camera.data_received', identifier, frm_num, frame]
      # super().on_data(data)
      # return data