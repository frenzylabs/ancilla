'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

from flask          import Flask, request
from flask_restful  import Resource, Api
from ...serial      import SerialConnection

class PortsResource(Resource):
  def get(self, id=None):
    return dict(
      baud_rates=SerialConnection.baud_rates(),
      ports=SerialConnection.list_ports()
    )
