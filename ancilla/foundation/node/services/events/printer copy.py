# class PrinterEvent(object):
#   CONNECTION_OPENED = "printer.connection.opened"
#   CONNECTION_FAILED = "printer.connection.failed"
#   CONNECTION_CLOSED = "printer.connection.closed"
#   STATE_CHANGED = "printer.state.changed"
#   PRINT_STARTED = "printer.print.started"


# class Dotdict(dict, metaclass=ServiceEvent):
#     """dot.notation access to dictionary attributes"""
#     # __getattr__ = dict.get
#     def all(obj = None):
#       print("INSIDE DOT dict all")
#       return dict

#     def __getattr__(self, name):
#       print("GET ATTR", self.__su)

#     __setattr__ = dict.__setitem__
#     __delattr__ = dict.__delitem__


# # The custom dictionary
# class member_table(dict):
#     def __init__(self):
#         self.member_names = {}
#     def __getitem__(self, key):
#         # if the key is not already defined, add to the
#         # list of keys.

#         if key not in self:
#             self.member_names[key] = dict.get(key)
#         # Call superclass
#         dict.__getitem__(self, key)

#     def getevent(cls, name):
#       print(f"GET EVENTS {cls.__name__} and {name}")      
#       print(cls.events)      
#       if cls.events.get(name):
#         res = cls.events[name]
#         return f"{cls.__name__.lower()}.{res}"
#       else:
#         for base in cls.__bases__:
#             if hasattr(base, 'getevent'):
#                 res = base.getevent(base, name)
#                 if res:
#                   return f"{cls.__name__.lower()}.{res}"


# class EventClass(type):
#     def find_event(self, key):
#       print(f"FIND EVENT {self}, {key}", flush=True)
#       key = key.lower()
#       if not self.lastClass:
#         self.lastClass = self.__class__      
#       res = self.lastClass.get_event(self.lastClass, key)
#       if res:
#         if type(res) != str:
#           self.lastClass = res
#         else:
#           key = res.lower()
#         self.current_events.append(key)
#       else:
#         raise AttributeError(f'{self.__class__.__name__}.{key} is invalid.')
#       return self
#     def get_event(cls, name):
#       if cls.events.get(name):
#         res = cls.events[name]
#         return res
#       else:
#         for base in cls.__bases__:
#             if hasattr(base, 'get_event'):
#                 res = base.get_event(base, name)
#                 if res:
#                   return res
#     def get_key(cls):
#       if cls.key == None:
#         return cls.__name__.lower()
#       return cls.key
#     def event_dict(cls, item = None):
#       if not item:
#         item = cls
#       if type(item) == str:
#         return item  
#       return dict(map(lambda kv: (kv[0], item.event_dict(kv[1])), item.events.items()))
#     def list_events(cls, key = None):
#       if key == None:
#         key = cls.get_key()
#       items = []
#       for k,v in cls.events.items():
#         if type(v) == str:
#           newkey = key + "." + v if key else v
#           items.append(newkey)
#         else:
#           newkey = key + "." + k if key else k
#           rv = v.list_events(newkey)
#           items.extend(rv)  
#       return items
#     @classmethod
#     def __prepare__(metacls, name, bases): 
#         return dict(events = dict(), key = None)
#     # The metaclass invocation
#     def __new__(cls, name, bases, classdict):
#         result = type.__new__(cls, name, bases, classdict)
#         result.events = classdict.get("events")
#         setattr(result, 'find_event', cls.find_event)
#         setattr(result, '__getattr__', cls.find_event)
#         setattr(result, 'list_events', classmethod(cls.list_events))
#         # setattr(result, '__str__', cls.__evtstr__)
#         result.get_event = cls.get_event
#         print(result)
#         return result
#     def __getattr__(cls, key):
#       inst = cls()
#       inst.find_event(key)
#       return inst
#       # return cls.getevent(cls, key)
#     # def __str__(self):
#     #   print("string", self.__name__)
#     #   return self.__name__
#     # def __evtstr__(self):
#     #   print(f"evtstring {self.current_events}")
#     #   print(f"classname = {self.__class__.__name__}", flush=True)
#     #   res = [self.__class__.__name__.lower()]
#     #   print(f"resevt = {res}", flush=True)
#     #   if self.current_events:
#     #     return ".".join([self.__class__.__name__.lower()] + self.current_events)
#     #   else:
#     #     return ""
#       # return ".".join(res) #self.__class__.__name + ". " +self.currentKey


# class Event(metaclass=EventClass):
#   key = None
#   def __init__(self, *args, **kwargs):
#       self.lastClass = None
#       self.current_events = []
#   def value(self):
#     res = [self.__class__.get_key()]
#     print(f"INSIDE VAL = {res}", flush=True)
#     if self.current_events:
#         res = res + self.current_events
#     return ".".join(res)
#   def __list_events__(self, key= None):    
#       if self.lastClass:
#         cls = self.lastClass
#       else:
#         cls = self.__class__
#       if not key:
#         key = self.value()
#       items = []
#       for k,v in cls.events.items():
#         print(f"k: {k}, v: {type(v)}, v: {v}", flush=True)
#         if type(v) == str:
#           newkey = key + "." + v if key else v
#           items.append(newkey)
#         else:
#           newkey = key + "." + k if key else k
#           rv = v.list_events(newkey)
#           items.extend(rv)  
#       return items
#   def __repr__(self):
#       return self.value()
#   # def find_event(self, key):
#   #     print(f"INSIDE EVENT FIND EVENT {self}, {key}")

# class State(Event):
#     events = dict(
#       changed = "changed"
#     )

# class PrinterState(State):
#     key = ""
#     events = dict(
#       other = "otherhere"
#     )    

# class Print(Event):
#   events = dict(
#     started = "started", 
#     paused = "paused",
#     state = PrinterState
#   )

# class Connection(Event):
#   events = dict(
#     opened = "opened", 
#     closed = "closed",
#     )  

# class Printer(Event):
#   events = dict(
#     added = "added",
#     deleted = "deleted",
#     connection = Connection,
#     print = Print,
#     state = State
#   )

# class Camera(Event):
#   events = dict(
#     recoding = "added",
#     connection = Connection,
#     state = State
#   )

# class EventBase(Event):
#   events = dict(test = "tada")  


# def test(event, payload = {}):
#   if event == 


# class SEvent(object, metaclass=EventClass):
#   toplevel = "seventhere"

#   def __init__(self, *args, **kwargs):
#     print("INSIDE INIT", type)
#     super().__init__(*args, **kwargs)    
#   def tada():
#     pass

# class EventBase(object):
#   events = dict(test = "tada")

#   @classmethod
#   def getevent(cls, name):
#       if cls.events.get(name):
#         res = cls.events[name]
#         return f"{cls.__name__.lower()}.{res}"
#       else:
#         for base in cls.__bases__:
#             # print("Bases = ", base)
#             if hasattr(base, 'getevent'):
#                 res = base.getevent(name)
#                 if res:
#                   print(f"REs for cls = {cls.__name__} res= {res}")
#                   return f"{cls.__name__.lower()}.{res}"

#   def getevent(cls, name):
#     print("GET Evt 1 ATTR", cls)
#     print(cls.events)
#     if cls.events.get(name):
#       return cls.events[name]
#     else:
#       print(super())
#       super().getevent(name)  



#   events = dict(test = "tada")
#   def getevent(cls, name):
#     print("INSIDE REGUlar get event")
#   @classmethod
#   def getevent(cls, name):
#     print("GET Evt 1 ATTR", cls)
#     print(cls.events)
#     if cls.events.get(name):
#       return cls.events[name]
#     return None
#     # else:
#     #   print(super())
#     #   super().getevent(name)  



#     @classmethod
#     def getevent(cls, name):
#       print("GET evt base ATTR", cls)
#       print(cls.events)
#       if cls.events.get(name):
#         return cls.events[name]
#       elif EventBase.events.get(name):
#         return EventBase.events[name]
#       else:
#         print(super())
#         return super().getevent(name)  



# class Event():
#   events = dict(test="blah")
#   @classmethod
#   def get_events(cls):
#     return cls.events


# class Conn(Event):
#   events = dict(CONNECTION_OPENED = "connection.opened", 
#     connection_closed = "connection.closed",
#     )

# class Printer(Event):
#   events = 

# class CE(BaseClass):
#   events = dict(CONNECTION_OPENED = "connection.opened", 
#     connection_closed = "connection.closed",
#     )
#   CONNECTION = "connection"
#   CONNECTION_OPENED = CONNECTION + ".opened"
#   CONNECTION_CLOSED = CONNECTION + ".closed"
  
#   def __init__(self, *args, **kwargs):
#     print("INSIDE INIT", type)
#     super().__init__(*args, **kwargs)    

# class ConnectionEvents(metaclass=ServiceEvent):
#   CONNECTION = "connection"
#   CONNECTION_OPENED = CONNECTION + ".opened"
#   CONNECTION_CLOSED = CONNECTION + ".closed"
#   events = dict(CONNECTION_OPENED = "connection.opened", 
#     connection_closed = "connection.closed",
#     )
#   @classmethod
#   def __getattr__(cls, name):
#     print("GET ATTR", cls)
#     print(cls.events)
#     if cls.events[name]:
#       return cls.events[name]
#   def __getattribute__(self, name):
#     print("GET ATTRIBUTE", self)
#     return super().__getattribute__(name)

# class ServiceEvent(type):
#   STATE         = "state"
#   STATE_CHANGED = "state.changed"
#   def __getattr__(cls, key):
#       print("INSIDE Service GEt attr", cls, key)
#       cls.__getattr__(key)

# class Events(object, metaclass=ServiceEvent):
#   events = dict(tada = "events")
#   @classmethod
#   def __getattr__(cls, name):
#     print("GET Event ATTR", cls)
#     print("Events", Events.events)
    
#     print(cls.events)
#     res = super().__getattr__(name)
#     print("EVENT REs ", res)
#     return res

# class PrinterEvent(Events, ConnectionEvents):
#   PRINTER = "printer"
#   PRINTER_PRINTS = PRINTER + ".print"
#   PRINT_STARTED = PRINTER + ".print.started"
#   events = dict(PRINT_STARTED = "printer.print.started")
#   @classmethod
#   def __getattr__(cls, name):
#     print("GET Printer ATTR")
#     print(PrinterEvent.events)
#     res = super().__getattr__(name)


#   CONNECTION = "connection"
#   CONNECTION_OPENED = CONNECTION + ".connection"



# class ServiceEvent(type):
#   toplevel = "event"
#   def all(obj = None):
#     return {}
#   def __getattr__(cls, key):
#       print("INSIDE Service GEt attr", key)
#       res = cls.all().get(key)
#       return res
#   def __repr__(cls):
#     return '%s' % cls.toplevel
#       # if res:
#       #   return cls.__name__ + "." + res
#       # return None

# # class ConnectionEvent(4metaclass=ServiceEvent):
# class TestEvent(metaclass=ServiceEvent): pass
# class ConnectionEvents(metaclass=ServiceEvent):
#   toplevel = "connection"
#   def all():
#     return dict(
#         opened = "opened",
#         failed = "failed",
#         closed = "closed"
#       )
#   def __repr__(self):
#     return "connection1"
#   def __str__(self):
#     return "connection2"


# class PrinterEvent(metaclass=ServiceEvent):  
#   toplevel = "printer"
#   service_type = "Printer"
#   CONNECTION = ConnectionEvents(self)
#   def all(obj = None):
#     print("INSIDE ALL", obj)
#     return Dotdict(dict(
#       connection=ConnectionEvents,
#       state=Dotdict(dict(
#         changed="changed"
#       )),
#       print=Dotdict(dict(
#         started="started"
#       ))
#     ))
#   def __getattr__(cls, key):
#       print("INSIDE GEt attr", key)
#       return cls.all().get(key)

#   __getattr__ = PrinterEvent.all.get

# PrinterEvent()

#   @property
#   def all(self):
#     return PrinterEvent._all()
    


# def flatten(d, parent_key='', sep='.'):
#     items = []
#     for k, v in d.items():
#         new_key = parent_key + sep + k if parent_key else k
#         if isinstance(v, collections.MutableMapping):
#             items.extend(flatten(v, new_key, sep=sep).items())
#         else:
#             items.append((new_key, v))
#     return dict(items)


# def event_dict(val):
  

# def event_dict(item):
#   if type(item) == str:
#     return item  
#   return dict(map(lambda kv: (kv[0], event_values(kv[1])), item.events.items()))


# def list_events(item, key=""):
#   items = []
#   for k,v in item.events.items():
#     if type(v) == str:
#       newkey = key + "." + v if key else v
#       items.append(newkey)
#     else:
#       newkey = key + "." + k
#       rv = fl(v, newkey)
#       items.extend(rv)  
#   return items


#     if type(rv) == str:
#       newkey = key + "." + rv
#     items[]
#      map(k, values(k, v))
#   key = key + 
  


# fl("printer", Printer)


#   for k,v in item.events.iteritems():
#     return map(k, values(k, v))
  

  

#   item.values()
#   # def all():
#   #    [getattr(self, attr) for attr in dir(self) if not callable(getattr(PrinterEvent, attr)) and not attr.startswith("__")]
# [self.events

# for (key, item) in self.events.items():

# my_dictionary = dict(map(lambda kv: (kv[0], event_values(kv[1])), Printer.events.items()))  


# [attr for attr in dir(PrinterEvent) if not callable(getattr(PrinterEvent, attr)) and not attr.startswith("__")]    