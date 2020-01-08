class EventClass(type):

    def find_event(self, key):
      key = key.lower()
      if not self.lastClass:
        self.lastClass = self.__class__      
      res = self.lastClass.get_event(self.lastClass, key)
      if res:
        if type(res) != str:
          self.lastClass = res
        else:
          key = res.lower()
        self.current_events.append(key)
      else:
        raise AttributeError(f'{self.__class__.__name__}.{key} is invalid.')
      return self

    def get_event(cls, name):
      if cls.events.get(name):
        res = cls.events[name]
        return res
      else:
        for base in cls.__bases__:
            if hasattr(base, 'get_event'):
                res = base.get_event(base, name)
                if res:
                  return res

    def get_key(cls):
      if cls.key == None:
        return cls.__name__.lower()
      return cls.key

    def event_dict(cls, item = None):
      if not item:
        item = cls
      if type(item) == str:
        return item  
      return dict(map(lambda kv: (kv[0], item.event_dict(kv[1])), item.events.items()))

    def list_events(cls, key= None):
      if key == None:
        key = cls.get_key()
      items = []
      for base in cls.__bases__:
        if hasattr(base, 'list_events'):
            res = base.list_events(key)
            if res:
              items.extend(res)
      for k,v in cls.events.items():
        if type(v) == str:
          newkey = key + "." + v if key else v
          items.append(newkey)
        else:
          newkey = key + "." + k if key else k
          rv = v.list_events(newkey)
          items.extend(rv)  
      return items

    @classmethod
    def __prepare__(metacls, name, bases): 
        return dict(events = dict())
    # def __init__(self, *args, **kwargs):
    #   self.lastClass = None
    #   self.currentEvents = []
    
    def __new__(cls, name, bases, classdict):
        result = type.__new__(cls, name, bases, classdict)
        result.events = classdict.get("events")
        # result.findevent = findevent
        setattr(result, 'find_event', cls.find_event)
        setattr(result, '__getattr__', cls.find_event)
        setattr(result, 'list_events', classmethod(cls.list_events))
        setattr(result, 'get_key', classmethod(cls.get_key))
        
        # setattr(result, '__str__', cls.__evtstr__)
        result.get_event = cls.get_event
        return result
    def __getattr__(cls, key):
      # print("INSIDE Service GEt attr", key)
      inst = cls()
      inst.find_event(key)
      return inst

