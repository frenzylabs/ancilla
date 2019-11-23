from .event_class import EventClass

class Event(metaclass=EventClass):
  key = None

  def __init__(self, *args, **kwargs):
      self.lastClass = None
      self.current_events = []

  def value(self):
    res = [self.__class__.get_key()]
    if self.current_events:
        res = res + self.current_events
    return ".".join(res)

  def __list_events__(self, key= None):    
      if self.lastClass:
        cls = self.lastClass
      else:
        cls = self.__class__
      if not key:
        key = self.value()
      items = []

      for k,v in cls.events.items():
        if type(v) == str:
          newkey = key + "." + v if key else v
          items.append(newkey)
        else:
          newkey = key + "." + k if key else k
          rv = v.list_events(newkey)
          items.extend(rv)  
      return items

  def __repr__(self):
      return self.value()


class State(Event):
    events = dict(
      changed = "changed"
    )

class Connection(Event):
  events = dict(
    opened = "opened", 
    closed = "closed",
    )  