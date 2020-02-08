'''
 layerkeep.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

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
    self.service.route('/projects/<path:re:.*>', 'GET', self.get_project)
    self.service.route('/profiles/<path:re:.*>', 'GET', self.get_profile)
    self.service.route('/projects', 'GET', self.list_projects)
    self.service.route('/profiles', 'GET', self.list_profiles)


  def _wrap_request(self, *args):
    pass

  async def features(self, request, *args):
    if not self.service.settings.get("auth.user.username"):
      return {"status": 401, "error": "Not Signed In"}
    url = f'{self.service.config.api_url}{self.service.settings["auth.user.username"]}/features'
    req = requests.Request('GET', url)
    response = await self.service.make_request(req)  
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
    return res

  async def list_projects(self, request, *args):
    res = await self.service.list_projects({"data": request.params})
    return res
  
  async def list_profiles(self, request, *args):
    res = await self.service.list_profiles({"data": request.params})
    return res

  async def get_project(self, request, path, *args):
    res = await self.service.get_project({"data": {"path": path, "params": request.params}})
    return res
  
  async def get_profile(self, request, path, *args):
    res = await self.service.get_profile({"data": {"path": path, "params": request.params}})
    return res


  async def create_printer(self, request, *args):
    if not self.service.settings.get("auth.user.username"):
      return {"status": 401, "error": "Not Signed In"}
    url = f'{self.service.config.api_url}{self.service.settings["auth.user.username"]}/printers'
    req = requests.Request('POST', url, json=request.params)
    response = await self.service.make_request(req)

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
    url = "{}{}".format(self.service.settings.base_url, "oauth/token")

    req = requests.Request('POST', url, headers=default_headers, json= payload)
    try:
      response = await self.service.make_request(req)


      if response.status_code == 200:

        tokenresp = response.body      
        auth = self.service.model.settings.get('auth') or {}
        auth['token'] = tokenresp
        self.service.model.settings.update(auth=auth)
        self.service.model.save()
        curuser = await self.current_user()

      return response
    except Exception as e:
      print(f"LK Signin Exception = {str(e)}", flush=True)
      raise e

