'''
 ports.py
 api

 Created by Wess Cope (me@wess.io) on 09/30/19
 Copyright 2019 Wess Cope
'''

import json

from .base      import BaseHandler

from serial.tools import list_ports

class PortsResource(BaseHandler):
  def get(self, *args, **kwargs):
    self.write(
      dict(
        baud_rates=PortsResource.baud_rates(),
        ports=PortsResource.list_ports()
      )
    )

    self.finish()


  @staticmethod
  def baud_rates():
    return [
      2_000_000,
      1_500_000,
      1_382_400,
      1_000_000,
      921_600,
      500_000,
      460_800,
      256_000,
      250_000,
      230_400,
      128_000,
      115_200,
      111_112,
      76_800,
      57_000,
      56_000,
      38_400,
      28_800,
      19_200,
      14_400,
      9600 
    ]

  @staticmethod
  def list_ports():
    return [port.device for port in list_ports.comports()]