'''
 camera_recording.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 11/08/19
 Copyright 2019 FrenzyLabs, LLC.
'''


from .base import BaseModel
from .camera import Camera
from .print import Print

from peewee import (
  CharField,
  TextField,
  IntegerField,
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
  print           = ForeignKeyField(Print, on_delete="SET NULL", related_name="recordings", null=True, default=None, backref='recordings')
  status          = CharField(null=True)
  reason          = CharField(null=True)
  
  layerkeep_id    = IntegerField(null=True)

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
      self.image_path,
      self.video_path
    )

  

  class Meta:
    table_name = "camera_recordings"

