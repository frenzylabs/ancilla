'''
 Ancilla.py
 ancilla

 Created by Wess Cope (me@wess.io) on 09/26/19
 Copyright 2019 Wess Cope
'''
from ancilla.app import Application

# from foundation.app import Application

# from foundation.api.server import APIServer

import tornado

if __name__ == "__main__":
  # APIServer().start()
  # Application().startup() #.main_loop()
  # tornado.ioloop.IOLoop.instance().start()
  # Application().startup() #.main_loop()
  Application('Ancilla', 'com.layerkeep.ancilla').main_loop()
