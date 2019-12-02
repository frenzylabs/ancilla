from .base import Event, Connection, State, Service

class CameraRecording(Event):
  events = dict(
    started = "started",
    failed = "failed",
    finished = "finished",
    state = State
  )

class Camera(Service):
  events = dict(
    recording = CameraRecording,
    connection = Connection,
    state = State,
    data_received = "data_received",
  )
