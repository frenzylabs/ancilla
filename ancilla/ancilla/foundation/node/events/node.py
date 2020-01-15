from .base import Event, State

class NodeEvent(Event):
  key = "node"
  events = dict(
    services = "created",
    updated = "updated",
    deleted = "deleted",
    state = State
  )

