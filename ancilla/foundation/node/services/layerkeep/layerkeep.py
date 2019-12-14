
# from ...events.printer import Printer as PrinterEvent
from ...base_service import BaseService
from ...api.layerkeep import LayerkeepApi
import requests
import asyncio
import functools
from ...response import AncillaResponse, AncillaError

import os
import hashlib
import base64
BLOCKSIZE = 65536



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
        "sync_file",
        "download_sliced_file"
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

        self.state["connected"] = True if access_token else False
        
        


    def load_config(self, dic):
      self.config.load_dict(self.default_config)
      self.config = self.config._make_overlay()
      self.config.load_dict(dic)


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

    async def make_request(self, req, content_type = 'json', auth = True, options = {}):
      prepped = self.session.prepare_request(req)
      if not auth:
        del prepped.headers['Authorization']
      # print(f"prepped = {prepped.headers}", flush=True)
      loop = asyncio.get_event_loop()
      makerequest = functools.partial(self.session.send, prepped, **options)

      future = loop.run_in_executor(None, makerequest)

      resp = await future
      return self.handle_response(resp, content_type)


    def handle_response(self, response, content_type='json'):
      # print(f"HandleResponse = {response}, {response.headers}", flush=True)
      resp = AncillaResponse(status=response.status_code)
      
      try:
        if content_type == 'json':
          resp.body = response.json()    
        else:
          resp.body = response.content
      except Exception as e:
        if not resp.success:
          resp.body = {"error": response.text}
        resp.exception = e
        raise resp
      return resp

      

    @check_authorization
    async def list_sliced_files(self, evt):
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
      

    @check_authorization
    async def create_printer(self, evt):
      try:
        payload = evt.get("data")
    
        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/printers'
        req = requests.Request('POST', url, json=payload)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"CREATe printer exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    @check_authorization
    async def update_printer(self, evt):
      try:
        payload = evt.get("data")

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/printers/{payload.get("layerkeep_id")}'
        req = requests.Request('PATCH', url, json=payload)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Update printer exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    @check_authorization
    async def delete_printer(self, evt):
      try:
        payload = evt.get("data")
        print(f"cp payload = {payload}", flush=True)    

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

    @check_authorization
    async def download_sliced_file(self, evt):
      try:
        payload = evt.get("data")
        print(f"cp payload = {payload}", flush=True)    

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/slices/{payload.get("id")}/gcodes'
        req = requests.Request('GET', url)
        response = await self.make_request(req, 'bytes')
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Download LK File exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    @check_authorization
    async def upload_sliced_file(self, evt):
      try:
        payload = evt.get("data")
        slice_params = payload.get("params") or {}
        sliced_file = payload.get("sliced_file")      
        filepath = sliced_file.get("path")  
        signparams = {
          "filepath": filepath,
          "name": sliced_file.get("name"),
          "kind": "slices"
        }

        ## Get an S3 Presigned Request To Upload directly to Bucket
        signed_response = await self.presign_asset({"data": signparams})

        direct_upload = {"filepath": filepath}
        direct_upload.update(signed_response.body.get("direct_upload"))
        print(f"direct_upload = {direct_upload}")    

        ## Upload sliced file to Bucket
        upload_response = await self.upload_file({"data": direct_upload})

        
        lkpayload = {
            "gcode": {"file": signed_response.body.get("signed_id")}
          }
        lkpayload.update(slice_params)

        # Create the SliceFile on Layerkeep
        response = await self.create_sliced_file({"data": lkpayload})
        return response
      
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Sync Sliced File exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)
        
    async def upload_file(self, evt):
      try:
        payload   = evt.get("data")

        url       = payload.get("url")
        filepath  = payload.get("filepath")
        method    = (payload.get("method") or "PUT").upper()
        headers   = {"Accept": "*/*"}
        headers.update(payload.get("headers") or {})

        with open(filepath, 'rb') as data:
          req = requests.Request(method, url, data=data, headers=headers)
          response = await self.make_request(req, content_type='text', auth=False, options = {"verify": False})

        return response

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Upload File exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    @check_authorization
    async def presign_asset(self, evt):
      try:
        payload = evt.get("data")

        filepath = payload.get("filepath")
        filename = payload.get("name")
        kind     = payload.get("kind")

        hasher = hashlib.md5()
        with open(filepath, 'rb') as afile:
            buf = afile.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(BLOCKSIZE)
        
        checksum = base64.b64encode(hasher.digest()).decode('utf-8')
        byte_size = os.stat(filepath).st_size

        presign_payload = {
          "byte_size": byte_size,
          "checksum": checksum,
          "content_type": "",
          "filename": filename
        }
        

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/{kind}/assets/presign'
        req = requests.Request('POST', url, json={"blob": presign_payload})
        response = await self.make_request(req)
        return response 

        # # response:

        # # direct_upload: {fields: {}, headers: {Content-Type: "", Content-MD5: "HkxfA5Qq/l9EuX30DYAIhg=="}, method: "put",…}
        # #     fields: {}
        # #     headers: {Content-Type: "", Content-MD5: "HkxfA5Qq/l9EuX30DYAIhg=="}
        # #     Content-MD5: "HkxfA5Qq/l9EuX30DYAIhg=="
        # #     Content-Type: ""
        # #     method: "put"
        # #     url: "https://layerkeep-dev.sfo2.digitaloceanspaces.com/cache/2019-12-13/1/slices/test.gcode?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=KRG33E7ANFWWSJOYGTKT%2F20191213%2Fsfo2%2Fs3%2Faws4_request&X-Amz-Date=20191213T175922Z&X-Amz-Expires=900&X-Amz-SignedHeaders=content-md5%3Bcontent-type%3Bhost&X-Amz-Signature=c01f7f0ff875ee5132e603c48d5b3ef9c49192c6da23bc63c4dbf93d550606c3"
        # # signed_id: "2019-12-13/1/slices/test.gcode"

      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"PresignAsset exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)
      pass

    @check_authorization
    async def create_sliced_file(self, evt):
      try:
        payload = evt.get("data")
        data = {"slice": payload}
        # data = {slice: {gcode: {file: "2019-12-13/1/slices/test.gcode"}}

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/slices'
        req = requests.Request('POST', url, json=data)
        response = await self.make_request(req)        
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"CREATe slicedFile exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)

    @check_authorization
    async def delete_sliced_file(self, evt):
      try:
        payload = evt.get("data")
        slice_id = payload.get("layerkeep_id")

        url = f'{self.settings.api_url}{self.settings.get("auth.user.username")}/slices/{slice_id}'
        req = requests.Request('DELETE', url)
        response = await self.make_request(req)
        return response
      except AncillaResponse as e:
        raise e
      except Exception as e:
        print(f"Delete slicedFile exception = {e}", flush=True)
        raise AncillaError(status= 400, body={"error": f"{str(e)}"}, exception=e)
