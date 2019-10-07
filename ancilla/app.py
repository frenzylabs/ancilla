'''
 app.py
 ancilla

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

import toga
import pathlib
import os
import threading

from .foundation.env  import Env

from .foundation import (
  Beacon,
  APIServer,
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
    self.beacon     = Beacon()
    self.api_server = APIServer()
    self.ws_server  = WSServer(self.api_server.app)

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
    self.api_server.start()
    
  
  def _start_prod(self):
    self.th = threading.Thread(target=self.api_server.start)
    self.th.start()

    self.window.show()

  def startup(self):
    self.setup_env()
    self.start_db()
    self.beacon.register()

    if Env.get('RUN_ENV') == 'DEV':
      self._start_dev()
    else:
      self._start_prod()    
