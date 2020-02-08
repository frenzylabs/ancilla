'''
 node.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .base import Event, State

class NodeEvent(Event):
  key = "node"
  events = dict(
    services = "created",
    updated = "updated",
    deleted = "deleted",
    state = State
  )

