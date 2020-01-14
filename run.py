#!/usr/bin/env python

'''
 run.py
 ancilla

 Created by Wess Cope (me@wess.io) on 01/13/20
 Copyright 2019 Wess Cope
'''

import sys
import tornado

from ancilla.app import Application

if __name__ == "__main__":
  app = None

  try:
      app = Application('Ancilla', 'com.layerkeep.ancilla')
      app.main_loop()
  except KeyboardInterrupt:
      print('Interrupted')    
      app.stop()
      sys.exit(0)
  
