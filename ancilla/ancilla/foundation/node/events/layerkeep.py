'''
 layerkeep.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .base import Event, Connection, State, Service

class LayerkeepEvent(Service):
  events = dict(
      authenticated = "authenticated"
    )
