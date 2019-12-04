from .base import Event, Connection, State, Service



class LayerkeepEvent(Service):
  events = dict(
      authenticated = "authenticated"
    )
