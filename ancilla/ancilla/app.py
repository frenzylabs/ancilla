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
  APIServer,
  Document
)

from .foundation.node.node_service import NodeService

from .foundation.data.db      import Database
from .foundation.data.models  import (
  Printer
)

from tornado.ioloop import IOLoop
import asyncio
from tornado.platform.asyncio import AnyThreadEventLoopPolicy

import atexit

class Application():
  
  def __init__(self, *args, **kwargs):
    # super().__init__(*args, **kwargs)    

    self.running = True
    self.setup_env()
    self.start_db()    
    self.document_store = Document()
    asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())

    if not IOLoop.current(instance=False):
      loop = IOLoop().initialize(make_current=True)  
    
    atexit.register(self.stop)
    
    
  def __del__(self):
    print(f"Delete Application ", flush=True)
    self.stop()
  
  def stop(self):
    print(f"Stop Application ", flush=True)
    if self.running:
      self.running = False      
      self.node_server.cleanup()
      self.api_server.stop()
      print("API ServerStopped")
      IOLoop.current().stop()
      

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


  def _start_dev(self):
    print("START DEV 1")
    # self.th = threading.Thread(target=self.api_server.start)
    # self.th.start()        
    # self.window.show()

    api_port = int(os.environ.get("API_PORT", 5000))
    self.node_server    = NodeService(api_port=api_port)
    self.api_server     = APIServer(self.document_store, self.node_server)
    self.api_server.start()
    
  
  def _start_prod(self):
    print("START PROD")
    api_port = int(os.environ.get("API_PORT", 5000))
    self.node_server    = NodeService(api_port=api_port) 
    self.api_server     = APIServer(self.document_store, self.node_server)
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
