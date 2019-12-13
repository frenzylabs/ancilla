import time
from .api import Api
from ..events import LayerkeepEvent
from ...data.models import Service, Printer, Camera

from ..response import AncillaResponse, AncillaError

import asyncio
import functools
import requests

class LayerkeepApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/sliced_files', 'GET', self.sliced_files)
    self.service.route('/sign_in', 'POST', self.sign_in)
    self.service.route('/sign_out', 'GET', self.sign_out)
    self.service.route('/current_user', 'GET', self.current_user)
    # self.service.route('/services/testing/<name>', 'GET', self.testname)
    # self.service.route('/test', 'GET', self.test)
    # self.service.route('/smodel/<model_id>', 'GET', self.service_model)
    # self.service.route('/smodel/<model_id>', ['POST', 'PATCH'], self.update_service_model)
    # self.service.route('/services/test', 'GET', self.test)
    # self.service.route('/services/camera', 'GET', self.listCameras)
    # self.service.route('/services/camera', 'POST', self.createCamera)
    # self.service.route('/services/printer', 'POST', self.createPrinter)
    # self.service.route('/services/printer', 'GET', self.listPrinters)
    # self.service.route('/services/<service>/<service_id><other:re:.*>', ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'], self.catchUnmountedServices)  
    # self.service.route('/services/<name><other:re:.*>', 'GET', self.catchIt)

  # _SERVICE_MODELS_ = ['printer', 'camera']
  def _wrap_request(self, *args):
    pass

  async def features(self, request, *args):
    print(f"requestparam = {request.params}", flush=True)    
    if not self.service.settings.get("auth.user.username"):
      return {"status": 401, "error": "Not Signed In"}
    url = f'{self.service.config.api_url}{self.service.settings["auth.user.username"]}/features'
    req = requests.Request('GET', url)
    response = await self.service.make_request(req)
    print(f"response = {response}", flush=True)    
    if response.status_code == 200:
      features = response.body    
      auth = self.service.model.settings.get('auth') or {}
      auth['features'] = features
      self.service.model.settings.update(auth=auth)
      self.service.model.save()
      return {"features": features}
    else:
      return {"status": 400, "error": "Could Not Sign In"}

  async def sliced_files(self, request, *args):
    res = await self.service.list_sliced_files({"data": request.params})
    print(f"Res = {res}", flush=True)
    return res
    # print(f"requestparam = {request.params}", flush=True)    
    # if not self.service.settings.get("auth.user.username"):
    #   return {"status": 401, "error": "Not Signed In"}
    # url = f'{self.service.config.api_url}{self.service.settings["auth.user.username"]}/slices'
    # req = requests.Request('GET', url, params=request.params)
    # response = await self.service.make_request(req)
    # print(f"response = {response}", flush=True)    
    # if response.status_code == 200:
    #   slices = response.json()    
    #   return slices      
    # elif response.status_code == 401:
    #   return {"status": 401, "error": "Unauthorized"}
    # else:
    #   return {"status": 400, "error": "Could Not Sign In"}

  async def create_printer(self, request, *args):
    print(f"requestparam = {request.params}", flush=True)    
    if not self.service.settings.get("auth.user.username"):
      return {"status": 401, "error": "Not Signed In"}
    url = f'{self.service.config.api_url}{self.service.settings["auth.user.username"]}/printers'
    req = requests.Request('POST', url, json=request.params)
    response = await self.service.make_request(req)
    print(f"response = {response}", flush=True)    
    if response.status_code == 200:
      printer = response.body    
      return printer
    elif response.status_code == 401:
      return {"status": 401, "error": "Unauthorized"}
    else:
      return {"status": 400, "error": "Could Not Sign In"}



  async def sign_out(self, request, *args):
    # url = "{}{}".format(self.service.config.api_url, "oauth/revoke")
    # req = requests.Request('POST', url, params={"token": self.service.settings["auth.token.access_token"]})
    self.service.model.settings.update(auth={})
    self.service.model.save()
    return {"status": 200, "message": "Successfully Signed Out"}


  async def current_user(self, *args):
    url = "{}{}".format(self.service.settings.api_url, "users/me")
    req = requests.Request('GET', url)

    response = await self.service.make_request(req)
    print(f"response = {response}", flush=True)    
    if response.status_code == 200:
      user = response.body      
      auth = self.service.model.settings.get('auth') or {}
      auth['user'] = user
      self.service.model.settings.update(auth=auth)
      self.service.model.save()
      # self.service.settings.update(token=tokenresp, namespace="auth")  
      return {"user": user}
    elif response.status_code == 401:
      return {"status": 401, "error": "Unauthorized"}
    else:
      return {"status": 400, "error": "Could Not Sign In"}


  async def sign_in(self, request, *args):
    payload = {
      'username'       : request.params.get("username"),
      'password'    : request.params.get("password"),
      'app'   : self.service.config["app"],
      'grant_type'  : 'password',
    }

    default_headers = {
      "Content-Type" : "application/json",
    }
    url = "{}{}".format(self.service.settings.api_url, "oauth/token")
    print(f"sign in url = {url}", flush=True)    
    req = requests.Request('POST', url, headers=default_headers, json= payload)

    response = await self.service.make_request(req)

    print(f"sign in response = {response}", flush=True)    
    if response.status_code == 200:
      print(f"response.json = {response.body}", flush=True)
      tokenresp = response.body      
      auth = self.service.model.settings.get('auth') or {}
      auth['token'] = tokenresp
      self.service.model.settings.update(auth=auth)
      self.service.model.save()
      curuser = await self.current_user()
      print(f"cur user = {curuser}", flush=True)
      # self.service.settings.update(token=tokenresp, namespace="auth")  
      # return {"token": tokenresp}
    # else:      
    #   response.body = {"error":}
    #   return {"status": 400, "error": "Could Not Sign In"}
    return response


    # return {'services': [service.json for service in Service.select()]}
