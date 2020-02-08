'''
 printer.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

from .base import Event, Connection, State, Service


class Print(Event):
  events = dict(
      started = "started", 
      paused = "paused",
      cancelled = "cancelled",
      finished = "finished",
      failed = "failed",
      state = State,
    )


class Printer(Service):
  events = dict(
      added = "added",
      deleted = "deleted",
      connection = Connection,
      print = Print,
    )
