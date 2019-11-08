'''
 printer.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base          import BaseHandler
from ...data.models import Camera

class CameraResource(BaseHandler):
  def get(self, *args, **kwargs):

    self.write(
      {'cameras': [camera.json for camera in Camera.select()]}
    )
    # self.finish()

  def post(self):
    camera = Camera(**self.params)
    
    if not camera.is_valid:
      self.write_error(400, errors=camera.errors)

    camera.save()
    self.write(camera.json)

    # self.finish()
