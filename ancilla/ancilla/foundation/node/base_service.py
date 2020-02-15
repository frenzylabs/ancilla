'''
 base_service.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/14/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import time
import sys
import zmq
import asyncio
from zmq.eventloop.zmqstream import ZMQStream

import functools
import json
from tornado.queues import Queue

from .events import Event, EventPack, Service as EventService

from ..data.models import Service

from .app import App

from ..utils.service_json_encoder import ServiceJsonEncoder
from ..utils import yields
from ..utils.dict import ConfigDict
from .response import AncillaResponse

from playhouse.signals import Signal, post_save

class BaseService(App):    

    __actions__ = [
        "get_state",
        "log_stuff"
      ]
    
    def __init__(self, model, **kwargs):
        super().__init__()
        self.connector = None

        self.model = model
        self.load_config(model.configuration)
        self.config._add_change_listener(
            functools.partial(self.config_changed, 'config'))
        # self.add_hook("config", functools.partial(self.settings_changed, "config"))
        self.name = model.name
        self.encoded_name = self.name.encode('ascii')
        self.identity = f"service{self.model.id}".encode('ascii')
        
        self.ctx = zmq.Context.instance()

          
        self.data_handlers = []
        self.task_queue = Queue()
        self.current_task = {}

        self.settings = self.config._make_overlay()
          
        # self.settings = ConfigDict()._make_overlay()        
        # def state_changed(event, oldstate, key, newval):
        #   print(f"INSIDE STATE CHANGED HOOK EVENT: {event}, {oldstate},  {key}, {newval}", flush=True)
        # st._add_change_listener(functools.partial(state_changed, 'state'))
        self.events = []



        self.pusher = self.ctx.socket(zmq.PUSH)
        self.pusher.connect(f"ipc://collector.ipc")

        event_stream = self.ctx.socket(zmq.SUB)
        event_stream.connect("ipc://publisher.ipc")
        self.event_stream = ZMQStream(event_stream)
        self.event_stream.linger = 0
        self.event_stream.on_recv(self.on_message)

        self.settings._add_change_listener(
            functools.partial(self.settings_changed, 'settings'))
        
        self.settings.load_dict(model.settings)

        self.event_handlers = ConfigDict()._make_overlay()        
        self.event_handlers._add_change_listener(
            functools.partial(self.events_changed, 'event'))
        self.event_handlers.update(model.event_listeners)

        self.state = ConfigDict()._make_overlay()
        self.state._add_change_listener(
            functools.partial(self.state_changed, 'state'))

        self.setup_routes()

        self.event_class = EventService

    def cleanup(self):
      print("cleanup service", flush=True)
      self.pusher.close()
      self.event_stream.close()
      # self.data_stream.close()

    def __del__(self):
      self.cleanup()

    def update_model(self, service_model):
      self.model = service_model
      self.name = service_model.name
      self.encoded_name = self.name.encode('ascii')
      if self.connector:
        # request = Request({"action": "update_", "body": msg})
        self.connector.update_model()
        # if yields(res):
        #   future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
          
        #   # zmqrouter = self.zmq_router
        #   def onfinish(fut):
        #     # res = b''
        #     try:
        #       newres = fut.result(1)     
        #     except Exception as a:
        #       # res = ar.encode()
        #       print(f'Event Handle Error {str(e)}')

        #   future.add_done_callback(onfinish)

    def load_config(self, dic):
      self.config.load_dict(dic)



    def events_changed(self, event, oldval, key, newval):
      # print(f"INSIDE event_changed CHANGED HOOK EVENT: {event}, {oldval},  {key}, {newval}", flush=True)
      if not newval:
        self.event_stream.setsockopt(zmq.UNSUBSCRIBE, key.encode('ascii'))
      else:
        # print(f"SUBSCRIBING TO event {key}", flush=True)
        self.event_stream.setsockopt(zmq.SUBSCRIBE, key.encode('ascii'))

    def config_changed(self, event, oldval, key, newval):
      # print(f"INSIDE config CHANGED HOOK EVENT: {event}, {oldval},  {key}, {newval}", flush=True)
      pass

    def settings_changed(self, event, oldval, key, newval):
      pass
      # print(f"INSIDE settings CHANGED HOOK EVENT: {event}, {oldval},  {key}, {newval}", flush=True)
      # self.event_stream.setsockopt(zmq.SUBSCRIBE, b"test")
      # self.event_stream.setsockopt(zmq.SUBSCRIBE, b"test")
      # if key == "event_handlers":
      #   oldkeys = []
      #   if "event_handlers" in oldval:
      #     oldkeys = oldval["event_handlers"].keys()
      #   newkeys = newval.keys()
      #   for t in oldkeys - newkeys:
      #     self.event_stream.setsockopt(zmq.UNSUBSCRIBE, t.encode('ascii'))
      #   for t in newkeys - oldkeys:
      #     self.event_stream.setsockopt(zmq.SUBSCRIBE, t.encode('ascii'))
      #   if key in oldval:

      #   for item in newval:

      # self.fire_event(self.event_class.state.changed, {f"{key}": newval})    

    def setup_routes(self):
      self.route('/state', 'GET', self.get_state)
      # self.route('/actions', 'GET', self.list_actions)
      # self.route('/options', ['GET', 'POST', 'PATCH', 'DELETE'], self.test)

    
    def state_changed(self, event, oldval, key, newval):
      # print(f"INSIDE STATE CHANGED HOOK EVENT: {event}, {oldval},  {key}, {newval}", flush=True)
      self.fire_event(self.event_class.state.changed, {f"{key}": newval})    

    def get_state(self, *args):      
      return self.state

    def log_stuff(self, epack, *args):
      # print(f"INSIDE LOG STUFF {epack.to_json()}", flush=True)
      pass


    def list_actions(self, *args):
      actions = []
      for base in self.__class__.__bases__:
            if hasattr(base, 'list_actions'):
                res = base.list_actions(base)
                if res:
                  actions = actions + res
      actions.extend(x for x in self.__actions__ if x not in actions)
      return actions

    def register_data_handlers(self, obj):
      self.data_handlers.append(obj)

    # def register_event_handler(self, evtname, action):
    #   if action in self.list_actions():
    #     self._event_hand
    #   self.event_stream.setsockopt(zmq.SUBSCRIBE, evtname)
    
    # def unsubscribe(self, to, topic=''):
    #   subscribetopic = to
    #   if len(topic) > 0:
    #     subscribetopic = f"{subscribetopic}.{topic}"
    #   subscribetopic = subscribetopic.encode('ascii')

    #     # if type(topic) != bytes:
    #     #   topic = topic.encode('ascii')
    #   print("subtopic= ", subscribetopic)
    #     # self.request.on_recv(callback)
    #   self.subscriber.setsockopt(zmq.UNSUBSCRIBE, subscribetopic)

    #   self.event_stream



    def on_message(self, msg):
      # print("ON MESSGE", msg)
      if not msg or len(msg) < 3:
        return
      topic, ident, pstring, *other = msg
      topic = topic.decode('utf-8')
      ident = ident.decode('utf-8')
      data = pstring.decode('utf-8')
      try:
        data = json.loads(data)
      except Exception as e:
        print(f"Received Invalid JSON Message - {str(e)}")

      epack = EventPack(topic, ident, data)
  
      el = self.event_handlers or {}
      for ekey in self.event_handlers.keys():
        if topic.startswith(ekey):
          for action_item in el.get(ekey) or []:
            action = action_item.get("action")
            if hasattr(self, action):
              method = getattr(self, action)
              # if method:
              #   method(epack)

              if method:
                res = b''
                try:
                  if len(self.plugins):
                    for plugin in self.plugins:
                      method = plugin.apply(method, self)

                  res = method({"data": data})
                except AncillaResponse as ar:
                  res = ar
                except Exception as e:
                  print(f"Handle Event Error  {str(e)}")
                  continue
                  # res = AncillaError(404, {"error": str(e)})
              # else:
              #   # newres = b'{"error": "No Method"}'
              #   res = AncillaError(404, {"error": "No Method"})
                # self.zmq_router.send_multipart([replyto, seq, err.encode()])
                # return

                if yields(res):
                  future = asyncio.run_coroutine_threadsafe(res, asyncio.get_running_loop())
                  
                  # zmqrouter = self.zmq_router
                  def onfinish(fut):
                    # res = b''
                    try:
                      newres = fut.result(1)     
                    except Exception as a:
                      # res = ar.encode()
                      print(f'Event Handle Error {str(e)}')

                  future.add_done_callback(onfinish)



    def on_data(self, data):
      # print("ON DATA", data)
      for d in self.data_handlers:
        data = d.handle(data)

      self.pusher.send_multipart(data)

    def stop(self):
      pass
    
    def start(self):
      pass

    

    async def _process_tasks(self):
      # print("About to get queue", flush=True)
      async for dtask in self.task_queue:
        # print('consuming {}...'.format(item))
        self.current_task[dtask.name] = dtask
        res = await dtask.run(self)
        rj = json.dumps(res, cls=ServiceJsonEncoder).encode('ascii')
        self.pusher.send_multipart([self.encoded_name+b'.task', b'finished', rj])

        # self.pusher.publish()
        del self.current_task[dtask.name]
        print(f"PROCESSED TASK = {res}", flush=True)

    async def _add_task(self, msg):
      await self.task_queue.put(msg)


    def fire_event(self, evtname, payload):
      # print(f"fire event {evtname}", flush=True)
      if isinstance(evtname, Event):
        evtname = evtname.value()
      evtname = evtname.encode('ascii')
      payload["device"] = self.name
      pstring = json.dumps(payload, cls=ServiceJsonEncoder)
      # print(f"JSON DUMP = {pstring}", flush=True)
      pstring = pstring.encode('ascii')
      self.pusher.send_multipart([b'events.'+ evtname, self.encoded_name, pstring])
      