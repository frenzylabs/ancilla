from .base import Event, State

class FileEvent(Event):
  key = "file"
  events = dict(
    created = "created",
    updated = "updated",
    deleted = "deleted",
    state = State
  )

