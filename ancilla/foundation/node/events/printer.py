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
