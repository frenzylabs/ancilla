'''
 base.py
 ancilla

 Created by Wess Cope (me@wess.io) on 10/08/19
 Copyright 2019 Wess Cope
'''

import json

from tornado.web    import RequestHandler
from tornado.escape import json_decode

class BaseHandler(RequestHandler):
  def set_default_headers(self):
    self.set_header('Access-Control-Allow-Origin', '*')
    self.set_header('Access-Control-Allow-Headers', '*')
    self.set_header('Access-Control-Max-Age', 1000)
    self.set_header('Content-type', 'application/json')
    self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    self.set_header('Access-Control-Allow-Headers', 'Content-Type, Access-Control-Allow-Origin, Access-Control-Allow-Headers, X-Requested-By, X-Requested-With, Access-Control-Allow-Methods')
  
  def prepare(self):
    if self.request.method == 'POST':
      self.params = json_decode(self.request.body)

  def options(self):
    pass
