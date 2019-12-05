import time
from .api import Api
from ..events import Event
from ...data.models import Service, Printer, Camera

import asyncio
import functools
import requests

class LayerkeepApi(Api):

  def setup(self):
    super().setup()
    self.service.route('/gcode_files', 'GET', self.gcodes)
    self.service.route('/sign_in', 'POST', self.sign_in)
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

  def gcodes(self, *args):
    allservices = []
    for service in Service.select():
      js = service.json
      model = service.model
      if model:
        js.update(model=model.to_json(recurse=False))
      allservices.append(js)
    
    return {'services': allservices}

  async def current_user(self, *args):
    url = "{}{}".format(self.service.config.api_url, "users/me")
    req = requests.Request('GET', url)
    prepped = self.service.session.prepare_request(req)
    print(f"prepped = {prepped.headers}", flush=True)
    print(f"session = {self.service.session.headers}", flush=True)
    loop = asyncio.get_event_loop()
    makerequest = functools.partial(self.service.session.send, prepped)
    # req = requests.Request('POST', url, headers=default_headers, params= payload)
    future = loop.run_in_executor(None, makerequest)
    # future = loop.run_in_executor(None, self.service.session.send, prepped)
    response = await future
    print(f"response = {response}", flush=True)    
    if response.status_code == 200:
      print(f"response.json = {response.json()}", flush=True)
      user = response.json()      
      auth = self.service.model.settings.get('auth') or {}
      auth['user'] = user
      self.service.model.settings.update(auth=auth)
      self.service.model.save()
      # self.service.settings.update(token=tokenresp, namespace="auth")  
      return {"user": user}
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
    url = "{}{}".format(self.service.config.api_url, "oauth/token")
    loop = asyncio.get_event_loop()
    postit = functools.partial(requests.post, url, headers=default_headers, json= payload)
    # req = requests.Request('POST', url, headers=default_headers, params= payload)
    future = loop.run_in_executor(None, postit)
    # future = loop.run_in_executor(None, requests.post, url=url, headers=default_headers, params= payload)
    response = await future

    print(f"response = {response}", flush=True)    
    if response.status_code == 200:
      print(f"response.json = {response.json()}", flush=True)
      tokenresp = response.json()      
      auth = self.service.model.settings.get('auth') or {}
      auth['token'] = tokenresp
      self.service.model.settings.update(auth=auth)
      self.service.model.save()
      # self.service.settings.update(token=tokenresp, namespace="auth")  
      return {"token": tokenresp}
    else:
      return {"status": 400, "error": "Could Not Sign In"}

    # return {'services': [service.json for service in Service.select()]}
