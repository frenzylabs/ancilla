
# from ...events.printer import Printer as PrinterEvent
from ...base_service import BaseService
from ...api.layerkeep import LayerkeepApi
import requests

class Layerkeep(BaseService):    
    
    __actions__ = [
        "sync_file"
      ]

    # events = PrinterEvents
    def __init__(self, model, **kwargs):
        self.session = requests.Session()

        super().__init__(model, **kwargs)
        

        # self.printer = PrinterModel.get(PrinterModel.service == model)
        # self.printer = model #query[0]
        
        self.api = LayerkeepApi(self)
        if "auth" not in self.model.settings:
          self.model.settings["auth"] = {}
          self.model.save()

        
        access_token = self.settings.get("auth.token.access_token")
        print(f"INIT {access_token}", flush=True)
        if access_token:          
          self.session.headers.update({'Authorization': f'Bearer {access_token}', "Content-Type" : "application/json"})
        # self.event_class = PrinterEvent
        # self.state = Dotdict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        # print(f"Printerevent {PrinterEvent.settings_changed.value()}", flush=True)
        
        # self.state.load_dict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        
        print(f"INSIDE Layerkeep INIT = {self.identity}", flush=True)
        # self.register_data_handlers(PrinterHandler(self))


    # @property
    # def actions(self):
    #   return [
    #     "get_state",
    #     "command"
    #   ]
    def set_access_token(self, *args):
      access_token = self.settings.get("auth.token.access_token")
      if access_token:          
        self.session.headers.update({'Authorization': f'Bearer {access_token}'})          

    def settings_changed(self, event, oldval, key, newval):
      print(f"INSIDE LK settings CHANGED HOOK EVENT: {event}, {oldval},  {key}, {newval}", flush=True)
      if not key.startswith("auth"):
        super().settings_changed(event, oldval, key, newval)
      else:
        print(f"AUTH CHANGED: {key}", flush=True)
        if key == "auth.token.access_token":
          self.session.headers.update({'Authorization': f'Bearer {newval}'})


    def test_hook(self, *args):
      print(f"LK TESTHOOK Fired: {args}", flush=True)
