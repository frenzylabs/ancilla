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

from .services.http_server        import HttpServer
from .services.serial_connection  import SerialConnection

class Application(toga.App):
  http_server       = HttpServer()
  serial_connection = SerialConnection(port="/dev/cu.usbserial-A107ZAQK", baudrate="115_200")

  @property
  def webview(self):
    _webview      = toga.WebView()
    _webview.url  = "http://127.0.0.1:5000/"
  
    return _webview

  @property
  def window(self):
    _window         = toga.MainWindow(title="Ancilla")
    _window.app     = self
    _window.content = self.webview

    return _window

  def open_document(self, url):
    pass
  
  def startup(self):
    th = threading.Thread(target=self.http_server.start)
    th.start()

    # self.serial_connection.start()
    self.window.show()
    
