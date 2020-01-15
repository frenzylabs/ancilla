'''
 Ancilla.py
 ancilla

 Created by Wess Cope (me@wess.io) on 09/26/19
 Copyright 2019 Wess Cope
'''
from ancilla.app import Application
import sys

# from foundation.app import Application

# from foundation.api.server import APIServer

import tornado

if __name__ == "__main__":
  # APIServer().start()
  # Application().startup() #.main_loop()
  # tornado.ioloop.IOLoop.instance().start()
  # Application().startup() #.main_loop()
  app = None
  try:
      app = Application('Ancilla', 'com.layerkeep.ancilla')
      app.main_loop()
  except KeyboardInterrupt:
      print('Interrupted')    
      app.stop()
      sys.exit(0)
  
