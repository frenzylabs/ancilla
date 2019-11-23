# from .event_class import Event
from .base import Event, Connection, State

class CameraRecording(Event):
  events = dict(
    started = "started",
    failed = "failed",
    state = State
  )

class Camera(Event):
  events = dict(
    recording = CameraRecording,
    connection = Connection,
    state = State
  )
