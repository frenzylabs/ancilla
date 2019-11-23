from .base import Event, Connection, State


class Print(Event):
  events = dict(
      started = "started", 
      paused = "paused",
      state = State,
    )


class Printer(Event):
  events = dict(
      added = "added",
      deleted = "deleted",
      connection = Connection,
      print = Print,
      state = State,
    )
