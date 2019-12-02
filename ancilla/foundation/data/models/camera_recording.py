'''
 printer.py
 models

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from .base import BaseModel
from .camera import Camera

from peewee import (
  CharField,
  TextField,
  ForeignKeyField
)

from playhouse.sqlite_ext import JSONField

class CameraRecording(BaseModel):
  task_name       = CharField(default="")
  image_path      = CharField()
  video_path      = CharField(null=True)
  settings        = JSONField(default={})
  camera          = ForeignKeyField(Camera, backref='recordings')
  camera_snapshot = JSONField(default={})
  status          = CharField(null=True)
  reason          = CharField(null=True)

  @property
  def serialize(self):
    return {
      'id':         self.id,
      'settings':   self.settings,
      'image_path':   self.image_path,
      'video_path':   self.video_path
    }


  def __repr__(self):
    return "{}, {}, {}".format(
      self.id, 
      self.settings, 
      self.image_path
    )

  

  class Meta:
    table_name = "camera_recordings"

