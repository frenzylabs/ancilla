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
import subprocess

from .env  import Env

from . import (
  Beacon,
  APIServer,
  Document,
  NodeServer
)

from .data.db      import Database
from .data.models  import (
  Printer, 
  PrinterLog
)

class Application(object):
  
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.document_store = Document()
    self.beacon         = Beacon()
    self.node_server    = NodeServer()
    self.api_server     = APIServer(self.document_store, self.node_server)
    

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
    print("START DEV", flush=True)
    # self.th = threading.Thread(target=self.api_server.start)
    # self.th.daemon = True
    # self.th.start()
    # subprocess.
    # self.api_server     = APIServer(self.document_store)
    
    self.api_server.start()
    
  
  def _start_prod(self):
    print("START PROD", flush=True)
    self.th = threading.Thread(target=self.api_server.start)
    self.th.start()

    self.window.show()

  def startup(self):
    self.setup_env()
    self.start_db()
    self.beacon.register()

    # if Env.get('RUN_ENV') == 'DEV':
    self._start_dev()
    # else:
    #   self._start_prod()    
