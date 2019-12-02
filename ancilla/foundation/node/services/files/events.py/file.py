from ....events import Event, State


class File(Event):
  events = dict(
      added = "added",
      deleted = "deleted",
      modified = "modified",
      state = State,
    )
