'''
 app.py
 ancilla

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import toga
import threading
import pathlib
import os

from .foundation.env import Env

from .foundation import (
  HttpServer,
  SerialConnection,
  WSServer
)

from .foundation.data.db      import Database
from .foundation.data.models  import (
  Printer, 
  PrinterLog
)

class Application(toga.App):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    self.http_server  = HttpServer()
    self.ws_server    = WSServer(self.http_server.app)

  @property
  def webview(self):
    _webview      = toga.WebView()
    _webview.url  = "http://127.0.0.1:5000/"
  
    return _webview

  @property
  def window(self):
    _window         = toga.MainWindow(title="Ancilla", size=(1000, 680))
    _window.app     = self
    _window.content = self.webview

    return _window

  def open_document(self, url):
    pass
  
  def setup_env(self):
    Env.setup()

  def start_db(self):
    Database.connect()
    Database.create_tables([
      Printer,
      PrinterLog
    ])

  def _start_dev(self):
    self.http_server.start()
    
  
  def _start_prod(self):
    self.th = threading.Thread(target=self.http_server.start)
    self.th.start()

    self.window.show()

  def startup(self):
    self.setup_env()
    self.start_db()

    if Env.get('RUN_ENV') == 'DEV':
      self._start_dev()
    else:
      self._start_prod()    
