'''
 file.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .base import Event, State

class FileEvent(Event):
  key = "file"
  events = dict(
    created = "created",
    updated = "updated",
    deleted = "deleted",
    state = State
  )

