'''
 http_server.py
 services

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import os

from flask import Flask, Response, send_from_directory
from flask_cors import CORS

UI_FOLDER = os.path.abspath("{}/../ui/dist".format(os.path.dirname(__file__)))

class HttpServer(object):
  class Action(object):
    def __init__(self, handler):
      self.handler  = handler

    def __call__(self, *args):
      return self.handler()


  app = Flask(
    "ancilla",
    static_folder=UI_FOLDER,
    static_url_path="/app"
  )

  def index(self, *args, **kwargs):
    return ""

  def start(self):
    self.app.add_url_rule('/', '/', HttpServer.Action(self.index))

    CORS(self.app)

    self.app.run(host='0.0.0.0', port=5000)
