'''
 app.py
 ancilla

 Created by Wess Cope (me@wess.io) on 09/24/19
 Copyright 2019 Wess Cope
'''

# import toga
import pathlib
import os
import threading
import subprocess

from .foundation.env  import Env

from .foundation import (
  Beacon,
  APIServer,
  Document
)

from .foundation.node.service import NodeService

from .foundation.data.db      import Database
from .foundation.data.models  import (
  Printer
)

import atexit

class Application():
  
  def __init__(self, *args, **kwargs):
    # super().__init__(*args, **kwargs)    
    self.beacon         = Beacon()
    self.setup_env()
    self.start_db()
    self.beacon.register()
    self.document_store = Document()
    self.node_server    = NodeService() # NodeServer()
    self.api_server     = APIServer(self.document_store, self.node_server, self.beacon)
    
    self.running = True
    atexit.register(self.stop)
    
    
  def __del__(self):
    print(f"Delete Application ", flush=True)
    self.stop()
  
  def stop(self):
    print(f"Stop Application ", flush=True)
    if self.running:
      self.running = False
      self.api_server.stop()
      self.beacon.close()
      self.node_server.cleanup()
      

  # @property
  # def webview(self):
  #   _webview      = toga.WebView()
  #   _webview.url  = "http://127.0.0.1:5000/"
  
  #   return _webview

  # @property
  # def window(self):
  #   _window         = toga.MainWindow(title="Ancilla", size=(1200, 680))
  #   _window.app     = self
  #   _window.content = self.webview
  #   return _window

  def open_document(self, url):
    pass
  
  def setup_env(self):
    Env.setup()

  def start_db(self):
    Database.connect()
    Database.run_migrations()
    # Database.create_tables([
    #   Printer,
    #   PrinterLog
    # ])

  def _start_dev(self):
    print("START DEV 1")
    # self.th = threading.Thread(target=self.api_server.start)
    # self.th.start()        
    # self.window.show()

    # self.th = threading.Thread(target=self.api_server.start)
    # self.th.daemon = True
    # self.th.start()
    # subprocess.
    
    # self.node_server    = NodeService() # NodeServer()
    # self.api_server     = APIServer(self.document_store, self.node_server)
    self.api_server.start()
    
  
  def _start_prod(self):
    print("START PROD")
    self.api_server.start()
    # self.node_server    = NodeService() # NodeServer()
    # self.th = threading.Thread(target=self.api_server.start)
    # self.th.start()
    # self.window.show()

  def main_loop(self):
    

    self._start_dev()
    # if Env.get('RUN_ENV') == 'DEV':
    #   self._start_dev()
    # else:
    #   self._start_prod()    
