'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base          import BaseHandler
from ...data.models import Camera, CameraRecording

class CameraRecordingResource(BaseHandler):
  def get(self, *args, **kwargs):

    self.write(
      {'cameras': [recording.json for recording in CameraRecording.select()]}
    )
    # self.finish()

  def post(self, recordingID):
    cr = CameraRecording.get_by_id(recordingID)
    
    kind = self.params.get('cameraID', None)
    name = self.params.get('name', None)
    camera = Camera(**self.params)
    
    if not camera.is_valid:
      self.write_error(400, errors=camera.errors)

    camera.save()
    self.finish({"camera": camera.json})
    # self.write(camera.json)

    # self.finish()
