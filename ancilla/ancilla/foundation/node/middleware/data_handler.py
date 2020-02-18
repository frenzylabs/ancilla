'''
 data_handler.py
 ancilla

 Created by Kevin Musselman (kevin@frenzylabs.com) on 01/08/20
 Copyright 2019 FrenzyLabs, LLC.
'''

import logging


class DataHandler(object):

  def __init__(self, service, *args):
    self.service = service
    self.logger = logging.getLogger(self.service.model.name)
    

  def handle(self, data):
    return data

