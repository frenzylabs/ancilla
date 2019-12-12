
# from ...events.printer import Printer as PrinterEvent
from ...base_service import BaseService
from ...api.layerkeep import LayerkeepApi
import requests
import asyncio
import functools
from ...response import AncillaResponse, AncillaError


def check_authorization(f):
    def wrapper(self, *args, **kwargs):
        print(f'Authusername = {self.settings.get("auth.user.username")}', flush=True)
        print(f'Settings = {self.settings}', flush=True)
        if not self.settings.get("auth.user.username"):
          raise AncillaError(status= 401, body={"error": "Not Signed In"})
        return f(self, *args, **kwargs)
    return wrapper


class Layerkeep(BaseService):    
    
    __actions__ = [
        "sync_file"
      ]

    # events = PrinterEvents
    def __init__(self, model, **kwargs):
        self.session = requests.Session()

        self.default_config = {"api_url": "https://layerkeep.com/", "app": "Ancilla"}
        

        super().__init__(model, **kwargs)
        

        # self.printer = PrinterModel.get(PrinterModel.service == model)
        # self.printer = model #query[0]
        
        self.api = LayerkeepApi(self)
        if "auth" not in self.model.settings:
          self.model.settings["auth"] = {}
          self.model.save()

        
        access_token = self.settings.get("auth.token.access_token")
        print(f"INIT {access_token}", flush=True)
        self.session.headers.update({"Content-Type" : "application/json", "Accept": "application/json"})
        if access_token:          
          self.session.headers.update({'Authorization': f'Bearer {access_token}'})
        # self.event_class = PrinterEvent
        # self.state = Dotdict({
        #   "status": "Idle",
        #   "connected": False, 
        #   "alive": False,
        #   "printing": False
        # })
        # print(f"Printerevent {PrinterEvent.settings_changed.value()}", flush=True)
        self.state["connected"] = True if access_token else False
        # self.state.load_dict({
        #   "connected": True if access_token else False
        # })
        
        print(f"INSIDE Layerkeep INIT = {self.identity}", flush=True)
        # self.register_data_handlers(PrinterHandler(self))


    def load_config(self, dic):
      self.config.load_dict(self.default_config)
      self.config = self.config._make_overlay()
      self.config.load_dict(dic)

    # @property
    # def actions(self):
    #   return [
    #     "get_state",
    #     "command"
    #   ]

    def test_hook(self, *args):
      print(f"LK TESTHOOK Fired: {args}", flush=True)

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

    async def make_request(self, req):
      prepped = self.session.prepare_request(req)
      print(f"prepped = {prepped.headers}", flush=True)
      loop = asyncio.get_event_loop()
      makerequest = functools.partial(self.session.send, prepped)
      # req = requests.Request('POST', url, headers=default_headers, params= payload)
      future = loop.run_in_executor(None, makerequest)
      # future = loop.run_in_executor(None, self.service.session.send, prepped)
      resp = await future
      return self.handle_response(resp)
      # return future
      # response = await future

    def handle_response(self, response):
      print(f"HandleResponse = {response}", flush=True)
      resp = AncillaResponse(status=response.status_code)
      
      try:
        resp.body = response.json()    
      except Exception as e:
        if not resp.success:
          resp.body = {"error": response.text}
        resp.exception = e
        raise resp
      return resp

      # if response.status_code >= 200 and response.status_code < 300:
      #     jresp = response.json()    
      #     return {"status": 200, "response": jresp}
      # elif response.status_code == 401:
      #   return {"status": 401, "error": "Unauthorized"}
      # else:
      #   return {"status": 400, "error": "Error"}
    # async def sign_in(self, evt):
    #   try:
    #     payload = evt.get("data")
    #     url = f'{self.config.api_url}{self.settings.get("auth.user.username")}/slices'

    @check_authorization
    async def list_gcode_files(self, evt):
      try:
        payload = evt.get("data")
        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/slices'
        req = requests.Request('GET', url, params=payload)
        response = await self.make_request(req)
        print(f"list gcode files response = {response}", flush=True)    
        # return self.handle_response(response)
        return response
        # if response.status_code == 200:
        #   slices = response.json()    
        #   return slices      
        # elif response.status_code == 401:
        #   return {"status": 401, "error": "Unauthorized"}
        # else:
        #   return {"status": 400, "error": "Could Not Sign In"}
      except Exception as e:
        print("Exception")
        raise e
      

    async def create_printer(self, evt):
      try:
        payload = evt.get("data")
        if not self.settings.get("auth.user.username"):
          raise AncillaError(status= 401, body={"error": "Not Signed In"})

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/printers'
        req = requests.Request('POST', url, json=payload)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"CREATe printer exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    async def update_printer(self, evt):
      try:
        payload = evt.get("data")
        if not self.settings.get("auth.user.username"):
          raise AncillaError(status= 401, body={"error": "Not Signed In"})

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/printers/{payload.get("layerkeep_id")}'
        req = requests.Request('PATCH', url, json=payload)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Update printer exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    async def delete_printer(self, evt):
      try:
        payload = evt.get("data")
        print(f"cp payload = {payload}", flush=True)    
        if not self.settings.get("auth.user.username"):
          raise AncillaError(status= 401, body={"error": "Not Signed In"})

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/printers/{payload.get("layerkeep_id")}'
        req = requests.Request('DELETE', url)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Delete printer exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)


    def create_print(self, evt):
      pass

    def create_slice_file(self, evt):
      pass